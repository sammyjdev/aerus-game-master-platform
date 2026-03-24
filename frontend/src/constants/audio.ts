import type { AudioCueKey } from '../types'

export const AUDIO_MAP: Record<AudioCueKey, string> = {
  sword_hit: '/audio/sword_hit.mp3',
  magic_fire: '/audio/magic_fire.mp3',
  magic_ice: '/audio/magic_ice.mp3',
  magic_lightning: '/audio/magic_lightning.mp3',
  loot_rare: '/audio/loot_rare.mp3',
  loot_epic: '/audio/loot_epic.mp3',
  loot_legendary: '/audio/loot_legendary.mp3',
  death_toll: '/audio/death_toll.mp3',
  level_up: '/audio/level_up.mp3',
  critical_hit: '/audio/critical_hit.mp3',
  critical_fail: '/audio/critical_fail.mp3',
  boss_appear: '/audio/boss_appear.mp3',
  eerie_ocean_ambience: '/audio/eerie_ocean.mp3',
  combat_intense: '/audio/combat_intense.mp3',
}

/**
 * Background 8-bit tracks that cycle when nothing special is happening.
 * Drop .mp3 files into /public/audio/idle/ and add their paths here.
 */
export const IDLE_TRACKS: string[] = [
  '/audio/idle/idle_01.mp3',
  '/audio/idle/idle_02.mp3',
  '/audio/idle/idle_03.mp3',
  '/audio/idle/idle_04.mp3',
]
