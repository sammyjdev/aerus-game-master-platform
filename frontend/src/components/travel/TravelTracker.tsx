import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useGameStore } from '../../store/gameStore';

const TERRAIN_COLOR: Record<string, string> = {
  road: '#2eb875',
  trail: '#e4b848',
  wilderness: '#e4b848',
  sea: '#4da6ff',
  mountain: '#9aa2c5',
  arctic: '#b8d8ff',
  corrupted: '#df5757',
};

export function TravelTracker() {
  const { t } = useTranslation();
  const travel = useGameStore((s) => s.gameState.world_state.travel);
  const lastEncounter = useGameStore((s) => s.lastTravelEncounter);
  const encounterRef = useRef<HTMLDivElement>(null);

  // Flash the panel red briefly when an encounter triggers
  useEffect(() => {
    if (!lastEncounter || !encounterRef.current) return;
    encounterRef.current.classList.add('travel-encounter-flash');
    const t = setTimeout(() => {
      encounterRef.current?.classList.remove('travel-encounter-flash');
    }, 2000);
    return () => clearTimeout(t);
  }, [lastEncounter]);

  if (!travel?.active) return null;

  const {
    origin_name = '',
    destination_name = '',
    day_current = 1,
    day_total = 1,
    terrain = 'wilderness',
    days_remaining = 0,
  } = travel;

  const progressPct = Math.min(
    100,
    Math.round((day_current / day_total) * 100),
  );
  const terrainLabel = t(`travel.terrain.${terrain}`, {
    defaultValue: terrain,
  });
  const terrainColor = TERRAIN_COLOR[terrain] ?? '#9aa2c5';

  return (
    <div className='travel-tracker' ref={encounterRef}>
      <div className='travel-header'>
        <span className='travel-icon'>🧭</span>
        <span className='travel-title'>{t('travel.in_transit')}</span>
      </div>

      <div className='travel-route'>
        {origin_name} → {destination_name}
      </div>

      <div className='travel-progress-row'>
        <div className='travel-progress-bar'>
          <div
            className='travel-progress-fill'
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <span className='travel-day-label'>
          {t('travel.day_counter', { current: day_current, total: day_total })}
        </span>
      </div>

      <div className='travel-footer'>
        <span className='travel-terrain-badge' style={{ color: terrainColor }}>
          {terrainLabel}
        </span>
        <span className='travel-days-remaining'>
          {days_remaining === 0
            ? t('travel.arriving_today')
            : t(
                days_remaining === 1
                  ? 'travel.days_remaining_one'
                  : 'travel.days_remaining_other',
                { count: days_remaining },
              )}
        </span>
      </div>

      {lastEncounter && (
        <div className='travel-encounter-alert'>
          {t('travel.encounter', { description: lastEncounter.description })}
        </div>
      )}
    </div>
  );
}
