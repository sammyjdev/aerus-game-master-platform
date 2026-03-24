export type Faction =
  | 'church_pure_flame'
  | 'empire_valdrek'
  | 'guild_of_threads'
  | 'children_of_broken_thread'

export type Race = 'human' | 'elf' | 'dwarf' | 'half-elf' | 'corrupted'

export type ItemRarity = 'common' | 'rare' | 'epic' | 'legendary'

export type PlayerStatus = 'alive' | 'dead' | 'spectator'

export type GameEventType =
  | 'DEATH'
  | 'LEVELUP'
  | 'BOSS_PHASE'
  | 'BOSS_DEFEATED'
  | 'LOOT'
  | 'MILESTONE'
  | 'CLASS_MUTATION'
  | 'FACTION_CONFLICT'
  | 'COOP_MISSION'
  | 'REPUTATION_CHANGE'
  | 'ABILITY_UNLOCK'
  | 'TRAVEL_ENCOUNTER'
  | 'TRAVEL_ARRIVED'

export interface Attributes {
  strength: number
  dexterity: number
  intelligence: number
  vitality: number
  luck: number
  charisma: number
}

export interface Item {
  item_id: string
  name: string
  description: string
  rarity: ItemRarity
  quantity: number
  equipped: boolean
}

export interface Condition {
  condition_id: string
  name: string
  description: string
  duration_turns: number | null
  applied_at_turn: number
  is_buff: boolean
}

export interface CurrencyWallet {
  copper: number
  silver: number
  gold: number
  platinum: number
}

export interface Milestone {
  name: string
  description: string
  attribute: keyof Attributes
  unlocked_at_points: number
}

export interface MacroAction {
  name: string
  template: string
}

export interface PlayerState {
  player_id: string
  name: string
  race: Race
  faction: Faction
  inferred_class: string
  level: number
  experience: number
  experience_next: number
  max_hp: number
  current_hp: number
  max_mp: number
  current_mp: number
  max_stamina: number
  current_stamina: number
  status: PlayerStatus
  backstory?: string
  attributes: Attributes
  inventory: Item[]
  currency: CurrencyWallet
  inventory_weight: number
  weight_capacity: number
  conditions: Condition[]
  magic_proficiency: Record<string, number>
  spell_aliases: Record<string, string>
  weapon_proficiency: Record<string, number>
  macros: MacroAction[]
  passive_milestones: Milestone[]
  contribution_score: number
}

export interface TravelState {
  active: boolean
  origin?: string
  origin_name?: string
  destination?: string
  destination_name?: string
  day_current?: number
  day_total?: number
  terrain?: string
  days_remaining?: number
}

export interface WorldState {
  current_location: string
  quest_flags: Record<string, string>
  tension_level: number
  campaign_paused: boolean
  travel?: TravelState
}

export interface HistoryEntry {
  role: 'user' | 'assistant'
  content: string
  turn_number: number
}

export interface GameState {
  campaign_id: string
  turn_number: number
  current_player: PlayerState
  other_players: PlayerState[]
  world_state: WorldState
  history: HistoryEntry[]
  is_streaming: boolean
  pending_dice_roll: DiceRollEvent | null
  pending_manual_roll: ManualDiceRequestEvent | null
  manual_roll_resolution: ManualDiceResolvedEvent | null
  isekai_narrative: string | null
  secret_objective: string
}

export interface NarrativeTokenEvent {
  type: 'narrative_token'
  token: string
}

export interface DiceRollEvent {
  type: 'dice_roll'
  player: string
  die: number
  purpose: string
  result: number
  is_critical: boolean
  is_fumble: boolean
}

export interface ManualDiceRequestEvent {
  type: 'request_dice_roll'
  roll_id: string
  roll_type: string
  dc: number
  description: string
}

export interface ManualDiceResolvedEvent {
  type: 'dice_roll_resolved'
  roll_id: string
  verdict: 'accept_with_bonus' | 'accept_no_bonus' | 'reject' | 'reroll_requested'
  circumstance_bonus: number
  final_result: number | null
  explanation: string
}

export interface ManualDiceArgumentSubmittedEvent {
  type: 'dice_argument_submitted'
  roll_id: string
  player_id: string
  initial_roll: number
  initial_result: number
  argument: string
  description: string
}

export interface PlayerDelta {
  hp_change?: number
  mp_change?: number
  stamina_change?: number
  experience_gain?: number
  attribute_changes?: Partial<Attributes>
  status?: PlayerStatus
  inventory_add?: Item[]
  inventory_remove?: string[]
  conditions_add?: Condition[]
  conditions_remove?: string[]
  magic_proficiency_delta?: Record<string, number>
  weapon_proficiency_delta?: Record<string, number>
}

export interface StateUpdateEvent {
  type: 'state_update'
  delta: Record<string, PlayerDelta>
}

export interface FullStateSyncEvent {
  type: 'full_state_sync'
  state: Omit<PlayerState, 'contribution_score'>
  world_state?: WorldState
}

export interface GameEvent {
  type: 'game_event'
  event: GameEventType
  payload: GameEventPayload
}

export type GameEventPayload =
  | DeathPayload
  | LevelUpPayload
  | LootPayload
  | MilestonePayload
  | ClassMutationPayload
  | BossPhasePayload
  | FactionConflictPayload
  | CoopMissionPayload
  | ReputationChangePayload
  | AbilityUnlockPayload

export interface DeathPayload {
  player_id: string
  player_name: string
  cause: string
}

export interface LevelUpPayload {
  player_id: string
  player_name: string
  new_level: number
  new_class?: string
}

export interface LootPayload {
  player_id: string
  player_name: string
  items: Item[]
}

export interface MilestonePayload {
  player_id: string
  player_name: string
  milestone_name: string
  milestone_description: string
  attribute: keyof Attributes
}

export interface ClassMutationPayload {
  player_id: string
  player_name: string
  old_class: string
  new_class: string
  reason: string
}

export interface BossPhasePayload {
  boss_name: string
  phase: number
  total_phases: number
}

export interface FactionConflictPayload {
  faction: Faction
  hint: string
}

export interface CoopMissionPayload {
  type: 'COOP_MISSION'
  active: boolean
  completed: boolean
  blocking: boolean
  required_players: number
  completed_players: number
  progress_percent: number
  objective: string
}

export interface ReputationChangePayload {
  type: 'REPUTATION_CHANGE';
  player_id: string;
  faction_id: string;
  delta: number;
  new_score: number;
}

export interface AbilityUnlockPayload {
  type: 'ABILITY_UNLOCK';
  player_id: string;
  player_name: string;
  level: number;
  inferred_class: string;
}

export interface StreamEndEvent {
  type: 'stream_end'
}

export interface GMThinkingEvent {
  type: 'gm_thinking'
  message: string
}

export interface TokenRefreshEvent {
  type: 'token_refresh'
  access_token: string
}

export type AudioCueKey =
  | 'sword_hit'
  | 'magic_fire'
  | 'magic_ice'
  | 'magic_lightning'
  | 'loot_rare'
  | 'loot_epic'
  | 'loot_legendary'
  | 'death_toll'
  | 'level_up'
  | 'critical_hit'
  | 'critical_fail'
  | 'boss_appear'
  | 'eerie_ocean_ambience'
  | 'combat_intense'

export interface AudioCueEvent {
  type: 'audio_cue'
  cue: AudioCueKey
}

export interface IsekaiConvocationEvent {
  type: 'isekai_convocation'
  narrative: string
  faction: Faction
  secret_objective: string
}

export interface BossMusicEvent {
  type: 'boss_music'
  url: string
}

export interface ImageReadyEvent {
  type: 'image_ready'
  url: string
  subject: 'boss' | 'character' | 'location'
}

export interface FactionObjectiveUpdateEvent {
  type: 'faction_objective_update'
  faction: Faction
  hint: string
}

export interface ErrorEvent {
  type: 'error'
  message: string
}

export interface HistorySyncEvent {
  type: 'history_sync'
  entries: Array<{ role: string; content: string }>
}

export type ServerEvent =
  | NarrativeTokenEvent
  | StreamEndEvent
  | DiceRollEvent
  | ManualDiceRequestEvent
  | ManualDiceResolvedEvent
  | ManualDiceArgumentSubmittedEvent
  | StateUpdateEvent
  | FullStateSyncEvent
  | GameEvent
  | GMThinkingEvent
  | TokenRefreshEvent
  | AudioCueEvent
  | IsekaiConvocationEvent
  | BossMusicEvent
  | ImageReadyEvent
  | FactionObjectiveUpdateEvent
  | HistorySyncEvent
  | ErrorEvent

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface CharacterResponse {
  player_id: string
  name: string
  race: Race
  faction: Faction
  inferred_class: string
  level: number
  attributes: Attributes
  status: PlayerStatus
  secret_objective: string
}

export interface RedeemLoginRequest {
  invite_code?: string
  username: string
  password: string
}

export interface CreateCharacterRequest {
  name: string
  race: Race
  faction: Faction
  backstory: string
}

export type DebugLevel = 'debug' | 'info' | 'warn' | 'error'

export interface DebugEntry {
  id: string
  timestamp: number
  level: DebugLevel
  scope: string
  message: string
  details?: unknown
}

export interface DebugStateSnapshot {
  server_time: number
  db_path: string
  player: {
    player_id: string
    username: string
    name: string | null
    faction: Faction | null
    inferred_class: string | null
    level: number
    status: PlayerStatus
    current_hp: number
    max_hp: number
    current_mp: number
    max_mp: number
    current_stamina: number
    max_stamina: number
    inventory_weight: number
    weight_capacity: number
    secret_objective_preview: string
  }
  world_state: {
    current_turn: number
    tension_level: number | string | null
    current_location: string | null
    campaign_paused: string | null
  }
  quest_flags: Record<string, string>
  recent_history: Array<{
    turn_number: number
    role: string
    content_preview: string
  }>
  runtime: {
    connected_players: number
    connected_player_ids: string[]
    history_rows: number
    players_rows: number
    alive_players: number
    encounter_scale_preview: number
    boss_scale_steps_preview: number
    pending_actions: number
    batch_task_active: boolean
    batch_window_seconds: number
  }
}
