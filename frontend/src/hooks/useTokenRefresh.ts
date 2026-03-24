import { useEffect } from 'react'

import { logClient } from '../debug/logger'
import { useGameStore } from '../store/gameStore'

const SEVEN_DAYS_SECONDS = 7 * 24 * 60 * 60

interface JWTPayload {
  exp?: number
}

function decodePayload(token: string): JWTPayload | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const json = atob(parts[1])
    return JSON.parse(json) as JWTPayload
  } catch {
    return null
  }
}

export function useTokenRefresh() {
  const token = useGameStore((state) => state.token)
  const setToken = useGameStore((state) => state.setToken)

  useEffect(() => {
    if (!token) return

    const payload = decodePayload(token)
    if (!payload?.exp) return

    const now = Math.floor(Date.now() / 1000)
    if (payload.exp <= now) {
      logClient('warn', 'auth', 'Token expired on client; clearing session')
      setToken(null)
      return
    }

    if (payload.exp - now < SEVEN_DAYS_SECONDS) {
      logClient('debug', 'auth', 'Token perto da janela de refresh; persistindo localmente', {
        expires_in_seconds: payload.exp - now,
      })
      localStorage.setItem('aerus_token', token)
    }
  }, [setToken, token])
}
