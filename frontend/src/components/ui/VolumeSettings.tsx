import { useState } from 'react'

import { useVolume } from '../../hooks/useAudio'

const CHANNELS = [
  { key: 'music' as const, label: 'Music' },
  { key: 'sfx' as const, label: 'Effects' },
  { key: 'ambient' as const, label: 'Ambient' },
]

export function VolumeSettings() {
  const { volume, setVolume } = useVolume()
  const [open, setOpen] = useState(false)

  return (
    <div className='volume-settings'>
      <button
        className='volume-toggle'
        onClick={() => setOpen((v) => !v)}
        aria-label='Volume settings'
        title='Volume'
      >
        {volume.music === 0 && volume.sfx === 0 ? 'ðŸ”‡' : 'ðŸ”Š'}
      </button>

      {open && (
        <div className='volume-panel'>
          {CHANNELS.map(({ key, label }) => (
            <label key={key} className='volume-row'>
              <span>{label}</span>
              <input
                type='range'
                min={0}
                max={1}
                step={0.05}
                value={volume[key]}
                onChange={(e) => setVolume({ [key]: Number(e.target.value) })}
              />
              <span className='volume-value'>{Math.round(volume[key] * 100)}%</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
