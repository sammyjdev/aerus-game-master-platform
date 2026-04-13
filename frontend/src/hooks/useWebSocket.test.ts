/**
 * useWebSocket.test.ts — Tests for the useWebSocket hook.
 * Covers WS message dispatching, store integration, and heartbeat.
 */
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useGameStore } from '../store/gameStore'
import { useWebSocket } from './useWebSocket'

// ── Stable audio spies ────────────────────────────────────────────────────

const mockPlaySound = vi.fn()
const mockPlayMusic = vi.fn()

vi.mock('./useAudio', () => ({
  useAudio: () => ({
    playSound: mockPlaySound,
    playMusic: mockPlayMusic,
    setVolume: vi.fn(),
    volume: { sfx: 0.8, music: 0.6, ambient: 0.2 },
  }),
}))

// ── WebSocket mock ────────────────────────────────────────────────────────

class MockWebSocket {
  static OPEN = 1 as const
  readyState: number = MockWebSocket.OPEN
  send = vi.fn()
  close = vi.fn()
  onopen: ((e: Event) => void) | null = null
  onclose: ((e: CloseEvent) => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: ((e: Event) => void) | null = null

  url: string
  constructor(url: string) { this.url = url }

  /** Helper: trigger onmessage with a JSON payload */
  triggerMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent)
  }

  /** Helper: trigger onopen */
  triggerOpen() {
    this.onopen?.(new Event('open'))
  }
}

let mockWsInstance: MockWebSocket

vi.stubGlobal(
  'WebSocket',
  class extends MockWebSocket {
    constructor(url: string) {
      super(url)
      mockWsInstance = this
    }
  },
)

// ── Test helpers ──────────────────────────────────────────────────────────

function resetStore() {
  useGameStore.setState(useGameStore.getInitialState())
}

function withPlayer(playerId: string) {
  useGameStore.setState((s) => ({
    ...s,
    gameState: {
      ...s.gameState,
      current_player: {
        ...s.gameState.current_player,
        player_id: playerId,
        current_hp: 100,
        max_hp: 100,
      },
    },
  }))
}

// ── Tests ─────────────────────────────────────────────────────────────────

describe('useWebSocket', () => {
  beforeEach(() => {
    resetStore()
    mockPlaySound.mockClear()
    mockPlayMusic.mockClear()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('narrative_token appends token to store narrative history', () => {
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({ type: 'narrative_token', token: 'Hello' })
    })

    const { history } = useGameStore.getState().gameState
    const narrativeEntry = history.find((e) => e.role === 'assistant')
    expect(narrativeEntry).toBeDefined()
    expect(narrativeEntry?.content).toContain('Hello')
  })

  it('state_update calls applyDelta for each player in the delta', () => {
    withPlayer('player-1')
    const spyApply = vi.spyOn(useGameStore.getState(), 'applyDelta')

    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({
        type: 'state_update',
        delta: { 'player-1': { hp_change: -10 } },
      })
    })

    expect(spyApply).toHaveBeenCalledWith('player-1', { hp_change: -10 })
  })

  it('game_event DEATH sets player status to dead', () => {
    withPlayer('player-1')
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({
        type: 'game_event',
        event: 'DEATH',
        payload: { player_id: 'player-1' },
      })
    })

    const { current_player } = useGameStore.getState().gameState
    expect(current_player.status).toBe('dead')
    expect(current_player.current_hp).toBe(0)
  })

  it('unknown WS message type does not throw and returns early', () => {
    renderHook(() => useWebSocket('test-token'))

    expect(() => {
      act(() => {
        mockWsInstance.triggerOpen()
        mockWsInstance.triggerMessage({ type: 'totally_unknown_event_xyz', foo: 'bar' })
      })
    }).not.toThrow()
  })

  it('malformed WS message (missing type) does not throw', () => {
    renderHook(() => useWebSocket('test-token'))

    expect(() => {
      act(() => {
        mockWsInstance.triggerOpen()
        mockWsInstance.triggerMessage({ not_a_type_field: true, data: 42 })
      })
    }).not.toThrow()
  })

  it('boss_music with high intensity plays boss_high music', () => {
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({
        type: 'boss_music',
        tension_level: 5,
        intensity: 'high',
      })
    })

    expect(mockPlayMusic).toHaveBeenCalledWith('boss_high')
  })

  it('boss_music with medium intensity plays boss_medium music', () => {
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({
        type: 'boss_music',
        tension_level: 3,
        intensity: 'medium',
      })
    })

    expect(mockPlayMusic).toHaveBeenCalledWith('boss_medium')
  })

  it('boss_music with url plays that url directly', () => {
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({
        type: 'boss_music',
        url: 'https://example.com/boss.mp3',
      })
    })

    expect(mockPlayMusic).toHaveBeenCalledWith('https://example.com/boss.mp3')
  })

  it('sends heartbeat ping every 30 seconds', () => {
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
    })

    // Advance time by 30 seconds
    act(() => {
      vi.advanceTimersByTime(30_000)
    })

    expect(mockWsInstance.send).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' }))
  })

  it('stream_end sets isStreaming to false', () => {
    useGameStore.setState((s) => ({ ...s, gameState: { ...s.gameState, is_streaming: true } }))
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({ type: 'stream_end' })
    })

    expect(useGameStore.getState().gameState.is_streaming).toBe(false)
  })

  it('gm_thinking sets gmThinking message', () => {
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({ type: 'gm_thinking', message: 'The GM is thinking...' })
    })

    expect(useGameStore.getState().gmThinking).toBe('The GM is thinking...')
  })

  it('audio_cue calls playSound with the cue key', () => {
    renderHook(() => useWebSocket('test-token'))

    act(() => {
      mockWsInstance.triggerOpen()
      mockWsInstance.triggerMessage({ type: 'audio_cue', cue: 'hit' })
    })

    expect(mockPlaySound).toHaveBeenCalledWith('hit')
  })

  it('null token does not open WebSocket', () => {
    renderHook(() => useWebSocket(null))

    expect(useGameStore.getState().connectionStatus).toBe('disconnected')
  })
})
