import { beforeEach, describe, expect, it } from 'vitest'

import { useGameStore } from './gameStore'

describe('gameStore', () => {
  beforeEach(() => {
    useGameStore.setState(useGameStore.getInitialState())
  })

  it('setToken — sets token in store', () => {
    useGameStore.getState().setToken('test-token-123')
    expect(useGameStore.getState().token).toBe('test-token-123')
  })

  it('setToken null — clears token', () => {
    useGameStore.getState().setToken('abc')
    useGameStore.getState().setToken(null)
    expect(useGameStore.getState().token).toBeNull()
  })

  it('setConnectionStatus — updates connection status', () => {
    useGameStore.getState().setConnectionStatus('connected')
    expect(useGameStore.getState().connectionStatus).toBe('connected')

    useGameStore.getState().setConnectionStatus('disconnected')
    expect(useGameStore.getState().connectionStatus).toBe('disconnected')
  })

  it('appendNarrativeToken — accumulates tokens into a single history entry', () => {
    useGameStore.getState().appendNarrativeToken('Hello')
    useGameStore.getState().appendNarrativeToken(', ')
    useGameStore.getState().appendNarrativeToken('World')

    const { history } = useGameStore.getState().gameState
    expect(history).toHaveLength(1)
    expect(history[0].role).toBe('assistant')
    expect(history[0].content).toBe('Hello, World')
  })

  it('applyDelta — applies hp_change to current player', () => {
    useGameStore.setState((state) => ({
      ...state,
      gameState: {
        ...state.gameState,
        current_player: {
          ...state.gameState.current_player,
          player_id: 'p1',
          current_hp: 100,
          max_hp: 100,
        },
      },
    }))

    useGameStore.getState().applyDelta('p1', { hp_change: -25 })

    expect(useGameStore.getState().gameState.current_player.current_hp).toBe(75)
  })

  it('handleGameEvent DEATH — marks player status as dead and zeroes hp', () => {
    useGameStore.setState((state) => ({
      ...state,
      gameState: {
        ...state.gameState,
        current_player: {
          ...state.gameState.current_player,
          player_id: 'p1',
          current_hp: 50,
          status: 'alive',
        },
      },
    }))

    useGameStore.getState().handleGameEvent({
      type: 'game_event',
      event: 'DEATH',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      payload: { player_id: 'p1' } as any,
    })

    const { current_player } = useGameStore.getState().gameState
    expect(current_player.status).toBe('dead')
    expect(current_player.current_hp).toBe(0)
  })

  it('handleGameEvent LEVELUP — updates player level', () => {
    useGameStore.setState((state) => ({
      ...state,
      gameState: {
        ...state.gameState,
        current_player: {
          ...state.gameState.current_player,
          player_id: 'p1',
          level: 5,
        },
      },
    }))

    useGameStore.getState().handleGameEvent({
      type: 'game_event',
      event: 'LEVELUP',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      payload: { player_id: 'p1', new_level: 6 } as any,
    })

    expect(useGameStore.getState().gameState.current_player.level).toBe(6)
  })

  it('setInitiativeOrder — stores initiative order correctly', () => {
    const order = [
      { player_id: 'p1', name: 'Alice', initiative: 18 },
      { player_id: 'p2', name: 'Bob', initiative: 12 },
    ]

    useGameStore.getState().setInitiativeOrder(order)

    expect(useGameStore.getState().initiative_order).toEqual(order)
  })

  it('setInitiativeOrder — updates current_actor_id when provided', () => {
    const order = [
      { player_id: 'p1', name: 'Alice', initiative: 18 },
      { player_id: 'p2', name: 'Bob', initiative: 12 },
    ]

    useGameStore.getState().setInitiativeOrder(order, 'p1')

    expect(useGameStore.getState().current_actor_id).toBe('p1')
  })

  it('setInitiativeOrder — does not override current_actor_id when not provided', () => {
    useGameStore.setState((state) => ({ ...state, current_actor_id: 'p2' }))

    useGameStore.getState().setInitiativeOrder([{ player_id: 'p1', name: 'Alice', initiative: 18 }])

    // null (default) does not override existing value
    expect(useGameStore.getState().current_actor_id).toBe('p2')
  })
})
