import { useCallback, useEffect, useRef } from 'react'

import { logClient, summarizeServerEvent } from '../debug/logger'
import { useAudio } from './useAudio'
import { useGameState } from './useGameState'
import { useGameStore } from '../store/gameStore'
import type { ServerEvent } from '../types'


const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
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
  const setIsStreaming = useGameStore((state) => state.setIsStreaming)
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
    const data = JSON.parse(event.data) as ServerEvent
    logClient('debug', 'ws', 'Mensagem recebida', summarizeServerEvent(data))
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
        Object.entries(data.delta).forEach(([playerId, delta]) => applyDelta(playerId, delta))
        break
      case 'full_state_sync':
        applyFullSync({ state: data.state, world_state: data.world_state })
        break
      case 'game_event':
        handleGameEvent(data)
        break
      case 'token_refresh':
        setToken(data.access_token)
        break
      case 'audio_cue':
        playSound(data.cue)
        break
      case 'boss_music':
        playMusic(data.url)
        break
      case 'stream_end':
        setIsStreaming(false)
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
        setIsekaiEvent(data)
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
  }, [appendNarrativeToken, applyDelta, applyFullSync, handleGameEvent, loadHistory, playMusic, playSound, setGmThinking, setIsekaiEvent, setIsStreaming, setManualRollResolution, setPendingDiceRoll, setPendingManualRoll, setServerError, setToken])

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
