import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useVolume } from '../../hooks/useAudio';

const CHANNELS = ['music', 'sfx', 'ambient'] as const;

export function VolumeSettings() {
  const { t } = useTranslation();
  const { volume, setVolume } = useVolume();
  const [open, setOpen] = useState(false);

  return (
    <div className='volume-settings'>
      <button
        className='volume-toggle'
        onClick={() => setOpen((v) => !v)}
        aria-label={t('game_ui.volume.aria_label')}
        title={t('game_ui.volume.title')}
      >
        {volume.music === 0 && volume.sfx === 0
          ? '\uD83D\uDD07'
          : '\uD83D\uDD0A'}
      </button>

      {open && (
        <div className='volume-panel'>
          {CHANNELS.map((key) => (
            <label key={key} className='volume-row'>
              <span>{t(`game_ui.volume.channels.${key}`)}</span>
              <input
                type='range'
                min={0}
                max={1}
                step={0.05}
                value={volume[key]}
                onChange={(e) => setVolume({ [key]: Number(e.target.value) })}
              />
              <span className='volume-value'>
                {Math.round(volume[key] * 100)}%
              </span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
