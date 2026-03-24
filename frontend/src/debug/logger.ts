import { useGameStore } from '../store/gameStore'
import type { DebugEntry, DebugLevel, ServerEvent } from '../types'

function clipText(value: string, limit = 160) {
  if (value.length <= limit) {
    return value
  }
  return `${value.slice(0, limit)}...`
}

function summarizeDetails(value: unknown, maxItems = 6): unknown {
  if (typeof value === 'string') {
    return clipText(value)
  }
  if (Array.isArray(value)) {
    if (value.length <= maxItems) {
      return value.map((item) => summarizeDetails(item, maxItems))
    }
    return [
      ...value.slice(0, maxItems).map((item) => summarizeDetails(item, maxItems)),
      `... +${value.length - maxItems} items`,
    ]
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
    return Object.fromEntries(
      entries.slice(0, maxItems).map(([key, item]) => [key, summarizeDetails(item, maxItems)]),
    )
  }
  return value
}

function createDebugEntry(
  level: DebugLevel,
  scope: string,
  message: string,
  details?: unknown,
): DebugEntry {
  const uuid = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
  return {
    id: uuid,
    timestamp: Date.now(),
    level,
    scope,
    message,
    details: details === undefined ? undefined : summarizeDetails(details),
  }
}

function writeConsole(entry: DebugEntry) {
  const prefix = `[AERUS:${entry.scope}] ${entry.message}`
  if (entry.level === 'error') {
    console.error(prefix, entry.details)
    return
  }
  if (entry.level === 'warn') {
    console.warn(prefix, entry.details)
    return
  }
  if (entry.level === 'info') {
    console.info(prefix, entry.details)
    return
  }
  console.debug(prefix, entry.details)
}

function shouldPersist(level: DebugLevel) {
  if (level === 'warn' || level === 'error') {
    return true
  }
  return useGameStore.getState().debugEnabled
}

export function logClient(
  level: DebugLevel,
  scope: string,
  message: string,
  details?: unknown,
) {
  const entry = createDebugEntry(level, scope, message, details)
  if (shouldPersist(level)) {
    useGameStore.getState().pushDebugEntry(entry)
  }
  if (shouldPersist(level) || level === 'warn' || level === 'error') {
    writeConsole(entry)
  }
}

export function setClientDebugEnabled(enabled: boolean) {
  useGameStore.getState().setDebugEnabled(enabled)
  const entry = createDebugEntry('info', 'debug', enabled ? 'Modo debug ativado' : 'Modo debug desativado')
  useGameStore.getState().pushDebugEntry(entry)
  writeConsole(entry)
}

export function summarizeServerEvent(event: ServerEvent) {
  return summarizeDetails(event)
}

declare global {
  interface Window {
    __AERUS_DEBUG__?: {
      getLogs: () => DebugEntry[]
      enable: () => void
      disable: () => void
      clear: () => void
    }
  }
}

if (typeof window !== 'undefined') {
  window.__AERUS_DEBUG__ = {
    getLogs: () => useGameStore.getState().debugEntries,
    enable: () => setClientDebugEnabled(true),
    disable: () => setClientDebugEnabled(false),
    clear: () => useGameStore.getState().clearDebugEntries(),
  }
}