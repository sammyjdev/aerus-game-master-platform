import { create } from 'zustand'

import type {
  DebugEntry,
  DiceRollEvent,
  FullStateSyncEvent,
  GameEvent,
  GameState,
  HistoryEntry,
  IsekaiConvocationEvent,
  ManualDiceRequestEvent,
  ManualDiceResolvedEvent,
  PlayerDelta,
  PlayerState,
  ReputationChangePayload,
} from '../types'

const DEBUG_STORAGE_KEY = 'aerus_debug_mode'

function readInitialDebugEnabled() {
  if (globalThis.window === undefined) {
    return import.meta.env.VITE_DEBUG_MODE === 'true'
  }

  const stored = localStorage.getItem(DEBUG_STORAGE_KEY)
  if (stored === 'true') {
    return true
  }
  if (stored === 'false') {
    return false
  }
  return import.meta.env.VITE_DEBUG_MODE === 'true'
}

const baseAttributes = {
  strength: 10,
  dexterity: 10,
  intelligence: 10,
  vitality: 10,
  luck: 10,
  charisma: 10,
}

const defaultPlayer: PlayerState = {
  player_id: '',
  name: '',
  race: 'human',
  faction: 'church_pure_flame',
  inferred_class: 'Adventurer',
  level: 1,
  experience: 0,
  experience_next: 100,
  max_hp: 100,
  current_hp: 100,
  max_mp: 50,
  current_mp: 50,
  max_stamina: 100,
  current_stamina: 100,
  status: 'alive',
  backstory: '',
  attributes: baseAttributes,
  inventory: [],
  currency: {
    copper: 0,
    silver: 5,
    gold: 0,
    platinum: 0,
  },
  inventory_weight: 0,
  weight_capacity: 80,
  conditions: [],
  magic_proficiency: {},
  spell_aliases: {},
  weapon_proficiency: {},
  macros: [],
  passive_milestones: [],
  contribution_score: 0,
  skills: {},
  attribute_points_available: 0,
  proficiency_points_available: 0,
  subrace: null,
}

function createInitialGameState(): GameState {
  return {
    campaign_id: 'default',
    turn_number: 0,
    current_player: defaultPlayer,
    other_players: [],
    world_state: {
      current_location: 'Unknown',
      quest_flags: {},
      tension_level: 0,
      campaign_paused: false,
    },
    history: [],
    is_streaming: false,
    pending_dice_roll: null,
    pending_manual_roll: null,
    manual_roll_resolution: null,
    isekai_narrative: null,
    secret_objective: '',
  }
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'

interface GameStore {
  token: string | null
  gameState: GameState
  connectionStatus: ConnectionStatus
  debugEnabled: boolean
  debugEntries: DebugEntry[]
  isekaiEvent: IsekaiConvocationEvent | null
  bufferedTokens: string[]
  tokensPaused: boolean
  eventLog: GameEvent[]
  gmThinking: string | null
  faction_reputations: Record<string, Record<string, number>> // player_id → faction_id → score
  lastTravelEncounter: { terrain: string; description: string; tier: number } | null
  serverError: string | null
  initiative_order: Array<{ player_id: string; name: string; initiative: number }>
  current_actor_id: string | null
  setToken: (token: string | null) => void
  setConnectionStatus: (status: ConnectionStatus) => void
  setDebugEnabled: (enabled: boolean) => void
  pushDebugEntry: (entry: DebugEntry) => void
  clearDebugEntries: () => void
  appendNarrativeToken: (token: string) => void
  completeNarrativeStream: () => void
  addHistoryEntry: (entry: HistoryEntry) => void
  setPendingDiceRoll: (roll: DiceRollEvent | null) => void
  setPendingManualRoll: (roll: ManualDiceRequestEvent | null) => void
  setManualRollResolution: (resolution: ManualDiceResolvedEvent | null) => void
  patchCurrentPlayer: (patch: Partial<PlayerState>) => void
  setIsStreaming: (value: boolean) => void
  applyDelta: (playerId: string, delta: PlayerDelta) => void
  applyFullSync: (payload: { state: FullStateSyncEvent['state']; world_state?: FullStateSyncEvent['world_state'] }) => void
  handleGameEvent: (event: GameEvent) => void
  setIsekaiEvent: (event: IsekaiConvocationEvent | null) => void
  setGmThinking: (message: string | null) => void
  setServerError: (message: string | null) => void
  loadHistory: (entries: { role: string; content: string; turn_number?: number }[]) => void
  setInitiativeOrder: (order: Array<{ player_id: string; name: string; initiative: number }>, currentActorId?: string | null) => void
}

function applyPlayerGameEvent(player: PlayerState, event: GameEvent): PlayerState {
  switch (event.event) {
    case 'DEATH': {
      const payload = event.payload as { player_id: string }
      if (payload.player_id !== player.player_id) {
        return player
      }
      return { ...player, status: 'dead', current_hp: 0 }
    }
    case 'LEVELUP': {
      const payload = event.payload as { player_id: string; new_level: number }
      if (payload.player_id !== player.player_id) {
        return player
      }
      return { ...player, level: payload.new_level }
    }
    case 'LOOT': {
      const payload = event.payload as { player_id: string; items: PlayerState['inventory'] }
      if (payload.player_id !== player.player_id) {
        return player
      }
      return { ...player, inventory: [...player.inventory, ...payload.items] }
    }
    case 'MILESTONE': {
      const payload = event.payload as {
        player_id: string
        milestone_name: string
        milestone_description: string
        attribute: keyof PlayerState['attributes']
      }
      if (payload.player_id !== player.player_id) {
        return player
      }
      const milestone = {
        name: payload.milestone_name,
        description: payload.milestone_description,
        attribute: payload.attribute,
        unlocked_at_points: 0,
      }
      return { ...player, passive_milestones: [...player.passive_milestones, milestone] }
    }
    case 'CLASS_MUTATION': {
      const payload = event.payload as { player_id: string; new_class: string }
      if (payload.player_id !== player.player_id) {
        return player
      }
      return { ...player, inferred_class: payload.new_class }
    }
    default:
      return player
  }
}

function mergeCooperativeMissionQuestFlags(
  baseFlags: Record<string, string>,
  payload: {
    active: boolean
    completed: boolean
    blocking: boolean
    required_players: number
    completed_players: number
    progress_percent: number
    objective: string
  },
): Record<string, string> {
  return {
    ...baseFlags,
    cooperative_mission_active: payload.active ? '1' : '0',
    cooperative_mission_completed: payload.completed ? '1' : '0',
    cooperative_mission_blocking: payload.blocking ? '1' : '0',
    cooperative_mission_required_players: String(payload.required_players),
    cooperative_mission_completed_players: String(payload.completed_players),
    cooperative_mission_progress_percent: String(payload.progress_percent),
    cooperative_mission_objective: payload.objective,
  }
}

export const useGameStore = create<GameStore>((set) => ({
  token: localStorage.getItem('aerus_token'),
  gameState: createInitialGameState(),
  connectionStatus: 'disconnected',
  debugEnabled: readInitialDebugEnabled(),
  debugEntries: [],
  isekaiEvent: null,
  bufferedTokens: [],
  tokensPaused: false,
  eventLog: [],
  gmThinking: null,
  faction_reputations: {},
  lastTravelEncounter: null,
  serverError: null,
  initiative_order: [],
  current_actor_id: null,
  setToken: (token) => {
    if (token) {
      localStorage.setItem('aerus_token', token)
    } else {
      localStorage.removeItem('aerus_token')
    }
    set({ token })
  },
  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),
  setDebugEnabled: (enabled) => {
    localStorage.setItem(DEBUG_STORAGE_KEY, enabled ? 'true' : 'false')
    set({ debugEnabled: enabled })
  },
  pushDebugEntry: (entry) =>
    set((state) => ({
      debugEntries: [...state.debugEntries, entry].slice(-250),
    })),
  clearDebugEntries: () => set({ debugEntries: [] }),
  setIsStreaming: (value) =>
    set((state) => ({
      gameState: { ...state.gameState, is_streaming: value },
    })),
  appendNarrativeToken: (token) =>
    set((state) => {
      if (state.tokensPaused) {
        return { bufferedTokens: [...state.bufferedTokens, token] }
      }

      const history = [...state.gameState.history]
      const gmThinking = null
      const last = history.at(-1)
      if (state.gameState.is_streaming && last?.role === 'assistant') {
        last.content = `${last.content}${token}`
      } else {
        history.push({
          role: 'assistant',
          content: token,
          turn_number: state.gameState.turn_number,
        })
      }

      return {
        gmThinking,
        gameState: {
          ...state.gameState,
          is_streaming: true,
          history,
        },
      }
    }),
  completeNarrativeStream: () =>
    set((state) => ({
      gameState: {
        ...state.gameState,
        is_streaming: false,
        turn_number: Math.max(
          state.gameState.turn_number,
          state.gameState.history.at(-1)?.turn_number ?? 0,
        ) + 1,
      },
    })),
  addHistoryEntry: (entry) =>
    set((state) => ({
      gameState: {
        ...state.gameState,
        history: [...state.gameState.history, entry],
      },
    })),
  setPendingDiceRoll: (roll) =>
    set((state) => {
      if (roll) {
        return {
          tokensPaused: true,
          gameState: { ...state.gameState, pending_dice_roll: roll },
        }
      }

      const history = [...state.gameState.history]
      if (state.bufferedTokens.length) {
        const chunk = state.bufferedTokens.join('')
        const last = history.at(-1)
        if (last?.role === 'assistant') {
          last.content = `${last.content}${chunk}`
        } else {
          history.push({
            role: 'assistant',
            content: chunk,
            turn_number: state.gameState.turn_number,
          })
        }
      }

      return {
        tokensPaused: false,
        bufferedTokens: [],
        gameState: {
          ...state.gameState,
          pending_dice_roll: null,
          is_streaming: false,
          history,
        },
      }
    }),
  setPendingManualRoll: (roll) =>
    set((state) => ({
      gameState: {
        ...state.gameState,
        pending_manual_roll: roll,
      },
    })),
  setManualRollResolution: (resolution) =>
    set((state) => ({
      gameState: {
        ...state.gameState,
        manual_roll_resolution: resolution,
      },
    })),
  patchCurrentPlayer: (patch) =>
    set((state) => ({
      gameState: {
        ...state.gameState,
        current_player: {
          ...state.gameState.current_player,
          ...patch,
        },
      },
    })),
  applyDelta: (playerId, delta) =>
    set((state) => {
      const isCurrentPlayer = state.gameState.current_player.player_id === playerId
      const target = isCurrentPlayer
        ? state.gameState.current_player
        : state.gameState.other_players.find((player) => player.player_id === playerId)

      if (!target) {
        return state
      }

      // Compute updated skills: first apply skill_use accumulation, then skill_delta overrides
      let updatedSkills = target.skills ?? {}

      if (delta.skill_use) {
        const { skill_key, impact } = delta.skill_use
        const current = updatedSkills[skill_key] ?? { rank: 0, uses: 0, impact: 0 }
        const newUses = current.uses + 1
        const newImpact = current.impact + impact
        let newRank = current.rank
        while (newImpact >= (newRank + 1) ** 2 * 2.0) {
          newRank += 1
        }
        updatedSkills = { ...updatedSkills, [skill_key]: { rank: newRank, uses: newUses, impact: newImpact } }
      }

      if (delta.skill_delta) {
        const merged = { ...updatedSkills }
        for (const [k, rank] of Object.entries(delta.skill_delta)) {
          merged[k] = { ...(merged[k] ?? { uses: 0, impact: 0 }), rank }
        }
        updatedSkills = merged
      }

      const updated: PlayerState = {
        ...target,
        current_hp: Math.max(0, target.current_hp + (delta.hp_change ?? 0)),
        current_mp: Math.max(0, target.current_mp + (delta.mp_change ?? 0)),
        current_stamina: Math.max(
          0,
          target.current_stamina + (delta.stamina_change ?? 0),
        ),
        experience: target.experience + (delta.experience_gain ?? 0),
        attributes: delta.attribute_changes
          ? { ...target.attributes, ...delta.attribute_changes }
          : target.attributes,
        status: delta.status ?? target.status,
        inventory: target.inventory
          .filter((item) => !(delta.inventory_remove ?? []).includes(item.item_id))
          .concat(delta.inventory_add ?? []),
        inventory_weight: target.inventory_weight,
        weight_capacity: target.weight_capacity,
        currency: target.currency,
        conditions: target.conditions
          .filter((condition) => !(delta.conditions_remove ?? []).includes(condition.condition_id))
          .concat(delta.conditions_add ?? []),
        magic_proficiency: delta.magic_proficiency_delta
          ? { ...target.magic_proficiency, ...delta.magic_proficiency_delta }
          : target.magic_proficiency,
        spell_aliases: target.spell_aliases,
        weapon_proficiency: delta.weapon_proficiency_delta
          ? { ...target.weapon_proficiency, ...delta.weapon_proficiency_delta }
          : target.weapon_proficiency,
        macros: target.macros,
        skills: updatedSkills,
        attribute_points_available: target.attribute_points_available + (delta.grant_attribute_points ?? 0),
        proficiency_points_available: target.proficiency_points_available + (delta.grant_proficiency_points ?? 0),
      }

      if (isCurrentPlayer) {
        return {
          gameState: {
            ...state.gameState,
            current_player: updated,
          },
        }
      }

      return {
        gameState: {
          ...state.gameState,
          other_players: state.gameState.other_players.map((player) =>
            player.player_id === playerId ? updated : player,
          ),
        },
      }
    }),
  applyFullSync: ({ state: statePayload, world_state }) =>
    set((state) => {
      const { secret_objective, ...playerFields } = statePayload as typeof statePayload & { secret_objective?: string }
      return {
        gameState: {
          ...state.gameState,
          turn_number: typeof world_state?.current_turn === 'number'
            ? world_state.current_turn
            : state.gameState.turn_number,
          secret_objective: secret_objective ?? state.gameState.secret_objective,
          world_state: world_state ?? state.gameState.world_state,
          current_player: {
            ...defaultPlayer,
            ...playerFields,
            contribution_score: 0,
          },
        },
      }
    }),
  handleGameEvent: (event) =>
    set((state) => {
      const updatedLog = [...state.eventLog, event].slice(-50)
      const player = applyPlayerGameEvent(state.gameState.current_player, event)

      if (event.event === 'REPUTATION_CHANGE') {
        const { player_id, faction_id, new_score } = event.payload as ReputationChangePayload
        return {
          eventLog: updatedLog,
          faction_reputations: {
            ...state.faction_reputations,
            [player_id]: {
              ...(state.faction_reputations[player_id] ?? {}),
              [faction_id]: new_score,
            },
          },
          gameState: { ...state.gameState, current_player: player },
        }
      }

      if (event.event === 'ABILITY_UNLOCK') {
        // ABILITY_UNLOCK is narrated by the GM inline; no state change needed
        return {
          eventLog: updatedLog,
          gameState: { ...state.gameState, current_player: player },
        }
      }

      if (event.event === 'BOSS_PHASE') {
        // Optionally log or trigger UI effect — no persistent state needed
        return {
          eventLog: updatedLog,
          gameState: { ...state.gameState, current_player: player },
        }
      }

      if (event.event === 'BOSS_DEFEATED') {
        return {
          eventLog: updatedLog,
          gameState: { ...state.gameState, current_player: player },
        }
      }

      if (event.event === 'FACTION_CONFLICT') {
        return {
          eventLog: updatedLog,
          gameState: { ...state.gameState, current_player: player },
        }
      }

      if (event.event === 'COOP_MISSION') {
        const payload = event.payload as {
          active: boolean
          completed: boolean
          blocking: boolean
          required_players: number
          completed_players: number
          progress_percent: number
          objective: string
        }
        const quest_flags = mergeCooperativeMissionQuestFlags(
          state.gameState.world_state.quest_flags,
          payload,
        )
        return {
          eventLog: updatedLog,
          gameState: {
            ...state.gameState,
            current_player: player,
            world_state: {
              ...state.gameState.world_state,
              quest_flags,
            },
          },
        }
      }

      if (event.event === 'TRAVEL_ENCOUNTER') {
        const payload = event.payload as unknown as {
          terrain: string;
          encounter?: { description: string; tier: number };
        }
        return {
          eventLog: updatedLog,
          lastTravelEncounter: {
            terrain: payload.terrain ?? 'wilderness',
            description: payload.encounter?.description ?? 'Unknown encounter',
            tier: payload.encounter?.tier ?? 1,
          },
          gameState: { ...state.gameState, current_player: player },
        }
      }

      if (event.event === 'TRAVEL_ARRIVED') {
        const payload = event.payload as unknown as {
          destination: string;
          destination_name: string;
        }
        return {
          eventLog: updatedLog,
          gameState: {
            ...state.gameState,
            current_player: player,
            world_state: {
              ...state.gameState.world_state,
              current_location: payload.destination ?? state.gameState.world_state.current_location,
              travel: { active: false },
            },
          },
        }
      }

      return {
        eventLog: updatedLog,
        gameState: { ...state.gameState, current_player: player },
      }
    }),
  setGmThinking: (gmThinking) => set({ gmThinking }),
  setServerError: (serverError) => set({ serverError }),
  loadHistory: (entries) =>
    set((state) => {
      const history = entries.map((entry, index) => ({
        role: entry.role as 'user' | 'assistant',
        content: entry.content,
        turn_number: entry.turn_number ?? index,
      }))
      const maxTurn = history.reduce(
        (currentMax, entry) => Math.max(currentMax, entry.turn_number),
        state.gameState.turn_number,
      )
      return {
        gameState: {
          ...state.gameState,
          history,
          turn_number: maxTurn,
        },
      }
    }),
  setIsekaiEvent: (isekaiEvent) =>
    set((state) => ({
      isekaiEvent,
      gameState: {
        ...state.gameState,
        isekai_narrative: isekaiEvent?.narrative ?? null,
        secret_objective: isekaiEvent?.secret_objective ?? state.gameState.secret_objective,
      },
    })),
  setInitiativeOrder: (order, currentActorId = null) =>
    set((state) => ({
      ...state,
      initiative_order: order,
      current_actor_id: currentActorId ?? state.current_actor_id,
    })),
}))
