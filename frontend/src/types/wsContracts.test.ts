import { describe, expect, it } from 'vitest'

import { parseWSMessage, safeParseWSMessage } from './wsContracts'

describe('wsContracts', () => {
  describe('parseWSMessage', () => {
    it('parses a valid narrative_token message', () => {
      const raw = { type: 'narrative_token', token: 'Hello' }
      const result = parseWSMessage(raw)
      expect(result.type).toBe('narrative_token')
      if (result.type === 'narrative_token') {
        expect(result.token).toBe('Hello')
      }
    })

    it('parses a valid dice_roll message with all required fields', () => {
      const raw = {
        type: 'dice_roll',
        player: 'Kael',
        die: 20,
        purpose: 'Attack',
        result: 17,
        is_critical: false,
        is_fumble: false,
      }
      const result = parseWSMessage(raw)
      expect(result.type).toBe('dice_roll')
      if (result.type === 'dice_roll') {
        expect(result.result).toBe(17)
        expect(result.die).toBe(20)
        expect(result.player).toBe('Kael')
      }
    })
  })

  describe('safeParseWSMessage', () => {
    it('returns null for an unknown message type', () => {
      const raw = { type: 'unknown_event', data: 'whatever' }
      expect(safeParseWSMessage(raw)).toBeNull()
    })

    it('returns null for a malformed structure (missing required field)', () => {
      // narrative_token requires `token`
      const raw = { type: 'narrative_token' }
      expect(safeParseWSMessage(raw)).toBeNull()
    })

    it('returns null for non-object input', () => {
      expect(safeParseWSMessage('just a string')).toBeNull()
      expect(safeParseWSMessage(null)).toBeNull()
      expect(safeParseWSMessage(42)).toBeNull()
    })

    it('correctly parses a boss_music message without url (backend real emit)', () => {
      const raw = {
        type: 'boss_music',
        tension_level: 4,
        intensity: 'high',
      }
      const result = safeParseWSMessage(raw)
      expect(result).not.toBeNull()
      expect(result?.type).toBe('boss_music')
    })

    it('discriminated union rejects wrong type literal on a known schema', () => {
      // dice_roll with wrong type literal should fail
      const raw = {
        type: 'dice_roll',
        player: 'Kael',
        die: 'not-a-number', // wrong type
        purpose: 'Attack',
        result: 17,
        is_critical: false,
        is_fumble: false,
      }
      expect(safeParseWSMessage(raw)).toBeNull()
    })
  })
})
