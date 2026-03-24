import { useCallback, useEffect, useRef, useSyncExternalStore } from 'react'
import { Howl } from 'howler'

import { AUDIO_MAP, IDLE_TRACKS } from '../constants/audio'
import type { AudioCueKey } from '../types'

export interface AudioVolume {
  sfx: number
  music: number
  ambient: number
}

const DEFAULT_VOLUME: AudioVolume = {
  sfx: 0.8,
  music: 0.6,
  ambient: 0.2,
}

function loadVolume(): AudioVolume {
  const saved = localStorage.getItem('aerus_volume')
  if (saved) {
    try {
      return JSON.parse(saved) as AudioVolume
    } catch {
      return DEFAULT_VOLUME
    }
  }
  return DEFAULT_VOLUME
}

// Simple external store so multiple components can read/write volume
let currentVolume: AudioVolume = loadVolume()
const listeners = new Set<() => void>()

function getVolumeSnapshot(): AudioVolume {
  return currentVolume
}

function subscribeVolume(cb: () => void) {
  listeners.add(cb)
  return () => { listeners.delete(cb) }
}

function setVolumeStore(next: AudioVolume) {
  currentVolume = next
  localStorage.setItem('aerus_volume', JSON.stringify(next))
  listeners.forEach((cb) => cb())
}

export function useVolume() {
  const volume = useSyncExternalStore(subscribeVolume, getVolumeSnapshot)

  const setVolume = useCallback((patch: Partial<AudioVolume>) => {
    setVolumeStore({ ...currentVolume, ...patch })
  }, [])

  return { volume, setVolume }
}

export function useAudio() {
  const musicRef = useRef<Howl | null>(null)
  const ambientRef = useRef<Howl | null>(null)
  const idleMusicRef = useRef<Howl | null>(null)
  const idleIndexRef = useRef(0)
  const volume = useSyncExternalStore(subscribeVolume, getVolumeSnapshot)

  // Keep currently-playing sources in sync with volume changes
  useEffect(() => {
    if (musicRef.current) musicRef.current.volume(volume.music)
    if (idleMusicRef.current) idleMusicRef.current.volume(volume.music)
    if (ambientRef.current) ambientRef.current.volume(volume.ambient)
  }, [volume])

  const stopIdleMusic = useCallback(() => {
    if (!idleMusicRef.current) return
    idleMusicRef.current.stop()
    idleMusicRef.current.unload()
    idleMusicRef.current = null
  }, [])

  const playNextIdleTrack = useCallback(() => {
    if (IDLE_TRACKS.length === 0) return

    stopIdleMusic()

    const track = IDLE_TRACKS[idleIndexRef.current % IDLE_TRACKS.length]
    idleIndexRef.current += 1

    const howl = new Howl({
      src: [track],
      volume: currentVolume.music,
      loop: false,
      onend: () => {
        playNextIdleTrack()
      },
    })

    idleMusicRef.current = howl
    howl.play()
  }, [stopIdleMusic])

  const startIdleMusic = useCallback(() => {
    if (idleMusicRef.current) return // already playing
    playNextIdleTrack()
  }, [playNextIdleTrack])

  const playSound = useCallback((key: AudioCueKey) => {
    const soundPath = AUDIO_MAP[key]
    if (!soundPath) return
    const sound = new Howl({ src: [soundPath], volume: currentVolume.sfx })
    sound.play()
  }, [])

  const playMusic = useCallback((url: string) => {
    stopIdleMusic()

    if (musicRef.current) {
      musicRef.current.stop()
      musicRef.current.unload()
    }

    musicRef.current = new Howl({
      src: [url],
      loop: true,
      volume: currentVolume.music,
    })

    musicRef.current.play()
  }, [stopIdleMusic])

  const stopMusic = useCallback(() => {
    if (musicRef.current) {
      musicRef.current.stop()
      musicRef.current.unload()
      musicRef.current = null
    }
  }, [])

  const playAmbient = useCallback((url: string) => {
    if (ambientRef.current) {
      ambientRef.current.stop()
      ambientRef.current.unload()
    }

    ambientRef.current = new Howl({
      src: [url],
      loop: true,
      volume: currentVolume.ambient,
    })

    ambientRef.current.play()
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      musicRef.current?.unload()
      ambientRef.current?.unload()
      idleMusicRef.current?.unload()
    }
  }, [])

  return { playSound, playMusic, stopMusic, playAmbient, startIdleMusic, stopIdleMusic }
}
