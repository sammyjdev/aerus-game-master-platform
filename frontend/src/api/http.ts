import type {
  CharacterResponse,
  CreateCharacterRequest,
  DebugStateSnapshot,
  MacroAction,
  RedeemLoginRequest,
  SkillEntry,
  SpendAttributePointsRequest,
  SpendProficiencyPointsRequest,
  TokenResponse,
} from '../types'
import { logClient } from '../debug/logger'

function getApiBase(): string {
  const env = import.meta.env.VITE_API_URL
  if (env && !env.includes('localhost')) return env
  if (typeof window !== 'undefined' && !window.location.hostname.includes('localhost')) {
    return window.location.origin
  }
  return env ?? 'http://localhost:8000'
}

const API_BASE = getApiBase()

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const startedAt = performance.now()
  const method = init?.method ?? 'GET'
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')

  logClient('debug', 'http', 'Request iniciada', {
    method,
    path,
  })

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string | { msg: string }[] }
    const detail = body.detail
    const message = Array.isArray(detail)
      ? detail.map((e) => e.msg).join(', ')
      : (detail ?? 'Request failed')
    logClient('error', 'http', 'Request falhou', {
      method,
      path,
      status: response.status,
      duration_ms: Number((performance.now() - startedAt).toFixed(2)),
      message,
    })
    throw new Error(message)
  }

  const payload = (await response.json()) as T
  logClient('info', 'http', 'Request completed', {
    method,
    path,
    status: response.status,
    duration_ms: Number((performance.now() - startedAt).toFixed(2)),
  })
  return payload
}

export function redeemInvite(payload: RedeemLoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/redeem', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function login(payload: RedeemLoginRequest): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createCharacter(
  token: string,
  payload: CreateCharacterRequest,
): Promise<CharacterResponse> {
  return request<CharacterResponse>('/character', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
}

export function getCharacter(token: string): Promise<CharacterResponse> {
  return request<CharacterResponse>('/character', {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function updateCharacterMacros(
  token: string,
  macros: MacroAction[],
): Promise<{ status: string; macros: MacroAction[] }> {
  return request<{ status: string; macros: MacroAction[] }>('/character/macros', {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ macros }),
  })
}

export function updateCharacterBackstory(
  token: string,
  backstory: string,
): Promise<{ status: string }> {
  return request<{ status: string }>('/character/backstory', {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ backstory }),
  })
}

export function updateCharacterSpellAliases(
  token: string,
  aliases: Record<string, string>,
): Promise<{ status: string; aliases: Record<string, string> }> {
  return request<{ status: string; aliases: Record<string, string> }>('/character/spell-aliases', {
    method: 'PUT',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ aliases }),
  })
}

export function registerByokKey(
  token: string,
  openrouterApiKey: string,
): Promise<{ message: string }> {
  return request<{ message: string }>('/player/byok', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ openrouter_api_key: openrouterApiKey }),
  })
}

interface SubmitManualDicePayload {
  roll_id: string
  initial_roll: number
  initial_result: number
  argument: string
}

export function submitManualDiceRoll(
  token: string,
  payload: SubmitManualDicePayload,
): Promise<{ status: string }> {
  return request<{ status: string }>('/dice/submit', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
}

export function getDebugStateSnapshot(token: string): Promise<DebugStateSnapshot> {
  return request<DebugStateSnapshot>('/debug/state', {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export interface AnalyzeBackstoryResponse {
  granted_skills: Record<string, SkillEntry>
  message: string
}

export function analyzeBackstory(token: string): Promise<AnalyzeBackstoryResponse> {
  return request<AnalyzeBackstoryResponse>('/character/analyze-backstory', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function spendAttributePoints(
  token: string,
  payload: SpendAttributePointsRequest,
): Promise<{ status: string; attribute: string; new_value: number; points_remaining: number }> {
  return request('/character/attributes/spend', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
}

export function spendProficiencyPoints(
  token: string,
  payload: SpendProficiencyPointsRequest,
): Promise<{ status: string; prof_type: string; key: string; new_rank: number; points_remaining: number }> {
  return request('/character/proficiencies/spend', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  })
}

// ── Admin API ────────────────────────────────────────────────────────────────

function adminRequest<T>(path: string, adminSecret: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  headers.set('X-Admin-Secret', adminSecret)
  return request<T>(path, { ...init, headers })
}

export interface AdminPlayer {
  player_id: string
  username: string
  name: string | null
  faction: string | null
  inferred_class: string | null
  level: number
  current_hp: number
  max_hp: number
  status: string
  is_alive: boolean
}

export interface AdminStatus {
  paused: boolean
  players: AdminPlayer[]
  tension_level: number
}

export function adminGetPlayers(adminSecret: string): Promise<AdminPlayer[]> {
  return adminRequest<AdminPlayer[]>('/admin/players', adminSecret)
}

export function adminPauseCampaign(adminSecret: string, paused: boolean): Promise<{ status: string }> {
  return adminRequest<{ status: string }>('/admin/pause', adminSecret, {
    method: 'POST',
    body: JSON.stringify({ paused }),
  })
}

export function adminGenerateInvite(adminSecret: string): Promise<{ invite_code: string }> {
  return adminRequest<{ invite_code: string }>('/admin/invite', adminSecret, {
    method: 'POST',
  })
}

export function adminReloadConfig(adminSecret: string): Promise<{ status: string }> {
  return adminRequest<{ status: string }>('/admin/reload', adminSecret, {
    method: 'POST',
  })
}

export { API_BASE }
