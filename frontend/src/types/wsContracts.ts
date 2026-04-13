/**
 * wsContracts.ts — Zod schemas for all incoming WebSocket messages.
 *
 * Mirror of backend/src/ws_contracts.py.
 * When adding a new WS event type, update BOTH files simultaneously.
 *
 * Usage:
 *   import { parseWSMessage } from './wsContracts'
 *   const parsed = parseWSMessage(rawJson)
 *   if (parsed.type === 'narrative_token') { ... }
 */
import { z } from 'zod'

// ── Narrative ────────────────────────────────────────────────────────────────

export const NarrativeTokenSchema = z.object({
  type: z.literal('narrative_token'),
  token: z.string(),
})

export const StreamEndSchema = z.object({
  type: z.literal('stream_end'),
})

export const GmThinkingSchema = z.object({
  type: z.literal('gm_thinking'),
  message: z.string(),
})

// ── Game State ───────────────────────────────────────────────────────────────

export const GameEventSchema = z.object({
  type: z.literal('game_event'),
  event: z.string(),
  payload: z.record(z.string(), z.unknown()),
})

export const StateUpdateSchema = z.object({
  type: z.literal('state_update'),
  delta: z.record(z.string(), z.unknown()),
})

export const FullStateSyncSchema = z.object({
  type: z.literal('full_state_sync'),
  state: z.record(z.string(), z.unknown()),
  world_state: z.record(z.string(), z.unknown()).optional(),
})

export const HistorySyncSchema = z.object({
  type: z.literal('history_sync'),
  entries: z.array(z.object({
    role: z.enum(['user', 'assistant']),
    content: z.string(),
    turn_number: z.number().int().optional(),
  })),
})

// ── Dice ─────────────────────────────────────────────────────────────────────

export const DiceRollSchema = z.object({
  type: z.literal('dice_roll'),
  player: z.string(),
  die: z.number().int().positive(),
  purpose: z.string(),
  result: z.number().int(),
  is_critical: z.boolean().default(false),
  is_fumble: z.boolean().default(false),
})

export const RequestDiceRollSchema = z.object({
  type: z.literal('request_dice_roll'),
  roll_id: z.string(),
  roll_type: z.string(),
  dc: z.number().int(),
  description: z.string(),
})

export const DiceRollResolvedSchema = z.object({
  type: z.literal('dice_roll_resolved'),
  roll_id: z.string(),
  verdict: z.enum(['accept_with_bonus', 'accept_no_bonus', 'reject', 'reroll_requested']),
  circumstance_bonus: z.number().int(),
  final_result: z.number().int().nullable(),
  explanation: z.string(),
})

// ── Audio / Media ────────────────────────────────────────────────────────────

export const AudioCueSchema = z.object({
  type: z.literal('audio_cue'),
  cue: z.string(),
})

export const BossMusicSchema = z.object({
  type: z.literal('boss_music'),
  tension_level: z.number().int().optional(),
  intensity: z.enum(['high', 'medium']).optional(),
  url: z.string().optional(),
})

export const ImageReadySchema = z.object({
  type: z.literal('image_ready'),
  url: z.string().url(),
  subject: z.string(),
})

// ── Auth ─────────────────────────────────────────────────────────────────────

export const TokenRefreshSchema = z.object({
  type: z.literal('token_refresh'),
  access_token: z.string(),
})

// ── Isekai ───────────────────────────────────────────────────────────────────

export const IsekaiConvocationSchema = z.object({
  type: z.literal('isekai_convocation'),
  faction: z.string(),
  narrative: z.string(),
  secret_objective: z.string(),
})

export const FactionObjectiveUpdateSchema = z.object({
  type: z.literal('faction_objective_update'),
  faction: z.string(),
  objective: z.string(),
  status: z.enum(['in_progress', 'completed', 'failed']),
  cred_change: z.number(),
})

// ── Errors ───────────────────────────────────────────────────────────────────

export const ErrorMessageSchema = z.object({
  type: z.literal('error'),
  message: z.string(),
})

// ── Discriminated union of all incoming messages ──────────────────────────────

export const WSMessageSchema = z.discriminatedUnion('type', [
  NarrativeTokenSchema,
  StreamEndSchema,
  GmThinkingSchema,
  GameEventSchema,
  StateUpdateSchema,
  FullStateSyncSchema,
  HistorySyncSchema,
  DiceRollSchema,
  RequestDiceRollSchema,
  DiceRollResolvedSchema,
  AudioCueSchema,
  BossMusicSchema,
  ImageReadySchema,
  TokenRefreshSchema,
  IsekaiConvocationSchema,
  FactionObjectiveUpdateSchema,
  ErrorMessageSchema,
])

export type WSMessage = z.infer<typeof WSMessageSchema>

/**
 * Parse and validate a raw WebSocket message payload.
 * Returns the typed message or throws a ZodError on invalid shape.
 */
export function parseWSMessage(raw: unknown): WSMessage {
  return WSMessageSchema.parse(raw)
}

/**
 * Safe version — returns null on parse failure instead of throwing.
 * Use for non-critical paths where a malformed message should be silently ignored.
 */
export function safeParseWSMessage(raw: unknown): WSMessage | null {
  const result = WSMessageSchema.safeParse(raw)
  return result.success ? result.data : null
}
