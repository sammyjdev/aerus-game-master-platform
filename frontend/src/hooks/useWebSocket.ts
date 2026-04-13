import { useCallback, useEffect, useRef } from 'react'

import { logClient, summarizeServerEvent } from '../debug/logger'
import { safeParseWSMessage } from '../types/wsContracts'
import { useAudio } from './useAudio'
import { useGameState } from './useGameState'
import { useGameStore } from '../store/gameStore'
import type { AudioCueKey, IsekaiConvocationEvent, PlayerDelta, ServerEvent } from '../types'


function getWsBase(): string {
  const env = import.meta.env.VITE_WS_URL
  if (env && !env.includes('localhost')) return env
  if (typeof window !== 'undefined' && !window.location.hostname.includes('localhost')) {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${proto}//${window.location.host}`
  }
  return env ?? 'ws://localhost:8000'
}

const WS_BASE = getWsBase()
const BACKOFF = [2000, 4000, 8000, 16000, 30000]

export function useWebSocket(token: string | null) {
  const socketRef = useRef<WebSocket | null>(null)
  const heartbeatRef = useRef<number | null>(null)
  const reconnectRef = useRef<number | null>(null)
  const attemptRef = useRef(0)
  const cancelledRef = useRef(false)
  const reconnectStartedAtRef = useRef<number | null>(null)
  const lastActionSentAtRef = useRef<number | null>(null)

  const setConnectionStatus = useGameStore((state) => state.setConnectionStatus)
  const setToken = useGameStore((state) => state.setToken)
  const setIsekaiEvent = useGameStore((state) => state.setIsekaiEvent)
  const completeNarrativeStream = useGameStore((state) => state.completeNarrativeStream)
  const setGmThinking = useGameStore((state) => state.setGmThinking)
  const setServerError = useGameStore((state) => state.setServerError)
  const {
    appendNarrativeToken,
    setPendingDiceRoll,
    setPendingManualRoll,
    setManualRollResolution,
    applyDelta,
    applyFullSync,
    handleGameEvent,
  } = useGameState()
  const loadHistory = useGameStore((state) => state.loadHistory)
  const { playSound, playMusic } = useAudio()

  const onMessage = useCallback((event: MessageEvent<string>) => {
    const raw = JSON.parse(event.data) as Record<string, unknown>
    const data = safeParseWSMessage(raw)
    if (data === null) {
      logClient('warn', 'ws', 'Unknown or malformed WS message', { raw })
      return
    }
    logClient('debug', 'ws', 'Mensagem recebida', summarizeServerEvent(data as unknown as ServerEvent))
    switch (data.type) {
      case 'narrative_token':
        appendNarrativeToken(data.token)
        break
      case 'dice_roll':
        setPendingDiceRoll(data)
        break
      case 'request_dice_roll':
        setPendingManualRoll(data)
        setManualRollResolution(null)
        break
      case 'dice_roll_resolved':
        setManualRollResolution(data)
        if (data.verdict !== 'reroll_requested') {
          setPendingManualRoll(null)
        }
        break
      case 'state_update':
        Object.entries(data.delta).forEach(([playerId, delta]) => applyDelta(playerId, delta as PlayerDelta))
        break
      case 'full_state_sync':
        applyFullSync({ state: data.state as Parameters<typeof applyFullSync>[0]['state'], world_state: data.world_state as Parameters<typeof applyFullSync>[0]['world_state'] })
        break
      case 'game_event':
        handleGameEvent(data as unknown as Parameters<typeof handleGameEvent>[0])
        break
      case 'token_refresh':
        setToken(data.access_token)
        break
      case 'audio_cue':
        playSound(data.cue as AudioCueKey)
        break
      case 'boss_music':
        if (data.url) {
          playMusic(data.url)
        } else {
          // Play based on intensity from emit
          playMusic(data.intensity === 'high' ? 'boss_high' : 'boss_medium')
        }
        break
      case 'image_ready':
        // No-op for now: FR-09 deferred
        logClient('debug', 'ws', 'image_ready received (deferred)', {})
        break
      case 'faction_objective_update':
        // No-op for now: W-03 pending
        logClient('debug', 'ws', 'faction_objective_update received', { faction: data.faction })
        break
      case 'stream_end':
        completeNarrativeStream()
        if (lastActionSentAtRef.current !== null) {
          const durationMs = Number((performance.now() - lastActionSentAtRef.current).toFixed(2))
          logClient('info', 'turn-metrics', 'Turn completed (stream_end)', {
            round_trip_ms: durationMs,
            action_sent_at: lastActionSentAtRef.current,
          })
          lastActionSentAtRef.current = null
        }
        break
      case 'isekai_convocation':
        setGmThinking(null)
        setIsekaiEvent(data as unknown as IsekaiConvocationEvent)
        break
      case 'gm_thinking':
        setGmThinking(data.message)
        break
      case 'history_sync':
        loadHistory(data.entries)
        break
      case 'error':
        logClient('warn', 'ws', 'Server-sent error', { message: data.message })
        setServerError(data.message ?? 'Unknown server error')
        break
      default:
        break
    }
  }, [appendNarrativeToken, applyDelta, applyFullSync, completeNarrativeStream, handleGameEvent, loadHistory, playMusic, playSound, setGmThinking, setIsekaiEvent, setManualRollResolution, setPendingDiceRoll, setPendingManualRoll, setServerError, setToken])

  const clearTimers = useCallback(() => {
    if (heartbeatRef.current) {
      globalThis.clearInterval(heartbeatRef.current)
      heartbeatRef.current = null
    }
    if (reconnectRef.current) {
      globalThis.clearTimeout(reconnectRef.current)
      reconnectRef.current = null
    }
  }, [])

  const sendHeartbeat = useCallback((ws: WebSocket) => {
    if (ws.readyState === WebSocket.OPEN) {
      logClient('debug', 'ws', 'Heartbeat enviado')
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }, [])

  const connect = useCallback((authToken: string) => {
    const openSocket = () => {
      if (cancelledRef.current) return

      setConnectionStatus(attemptRef.current > 0 ? 'reconnecting' : 'connecting')
      logClient('info', 'ws', 'Opening WebSocket connection', {
        attempt: attemptRef.current,
        url: `${WS_BASE}/ws/<token>`,
      })
      const ws = new WebSocket(`${WS_BASE}/ws/${authToken}`)
      socketRef.current = ws

      ws.onopen = () => {
        const wasReconnecting = attemptRef.current > 0
        const reconnectStart = reconnectStartedAtRef.current
        const reconnectDuration = reconnectStart === null
          ? null
          : Number((performance.now() - reconnectStart).toFixed(2))
        attemptRef.current = 0
        setConnectionStatus('connected')
        logClient('info', 'ws', 'WebSocket conectado')
        if (wasReconnecting) {
          logClient('info', 'ws-metrics', 'Reconnection completed', {
            reconnect_duration_ms: reconnectDuration,
          })
          reconnectStartedAtRef.current = null
        }
        heartbeatRef.current = globalThis.setInterval(sendHeartbeat, 30000, ws)
      }

      ws.onmessage = onMessage

      ws.onclose = () => {
        clearTimers()
        if (cancelledRef.current) return
        const delay = BACKOFF[Math.min(attemptRef.current, BACKOFF.length - 1)]
        reconnectStartedAtRef.current ??= performance.now()
        attemptRef.current += 1
        logClient('warn', 'ws', 'WebSocket closed; scheduling reconnect', {
          next_attempt: attemptRef.current,
          delay_ms: delay,
        })
        reconnectRef.current = globalThis.setTimeout(openSocket, delay)
      }

      ws.onerror = () => {
        logClient('error', 'ws', 'WebSocket connection error')
        ws.close()
      }
    }

    openSocket()
  }, [clearTimers, onMessage, sendHeartbeat, setConnectionStatus])

  useEffect(() => {
    if (!token) {
      setConnectionStatus('disconnected')
      return
    }

    cancelledRef.current = false
    connect(token)

    return () => {
      cancelledRef.current = true
      clearTimers()
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [clearTimers, connect, setConnectionStatus, token])

  const sendAction = useCallback((text: string) => {
    const socket = socketRef.current
    if (socket?.readyState !== WebSocket.OPEN) {
      logClient('warn', 'ws', 'Tried to send action without an open connection', {
        readyState: socket?.readyState,
      })
      return
    }

    logClient('info', 'action', 'Action sent from frontend', {
      preview: text.slice(0, 180),
      length: text.length,
    })
    lastActionSentAtRef.current = performance.now()
    socket.send(JSON.stringify({ action: text }))
  }, [])

  return { sendAction }
}
