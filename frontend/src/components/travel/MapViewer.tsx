import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

function getApiBase(): string {
  const env = import.meta.env.VITE_API_URL;
  if (env && !env.includes('localhost')) return env;
  if (
    typeof window !== 'undefined' &&
    !window.location.hostname.includes('localhost')
  ) {
    return window.location.origin;
  }
  return env ?? 'http://localhost:8000';
}

const API_BASE = getApiBase();

const MAPS = [
  { label: 'map.world', file: 'Aerus_Mapa_Mundi.png', translatable: true },
  { label: 'Myr', file: 'Aerus_IslandOfMyr_Map.png', translatable: false },
  { label: 'Valdoria', file: 'Areus_Valdoria_Map.png', translatable: false },
  { label: 'Shaleth', file: 'Aerus_Shaleth_Map.png', translatable: false },
  { label: 'Estravar', file: 'Aerus_Estravar_Map.png', translatable: false },
  { label: 'Khorrath', file: 'Aerus_Khorrath_Map.png', translatable: false },
  { label: 'Veth', file: 'Aerus_Veth_Map.png', translatable: false },
];

export function MapViewer() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open]);

  return (
    <>
      <button
        className='map-viewer-toggle'
        onClick={() => setOpen((v) => !v)}
        title={t('map.button_title')}
        aria-label={t('map.open_label')}
      >
        🗺
      </button>

      {open && (
        <div className='map-viewer-backdrop' onClick={() => setOpen(false)}>
          <div
            className='map-viewer-modal'
            onClick={(e) => e.stopPropagation()}
            role='dialog'
            aria-modal='true'
            aria-label={t('map.title')}
          >
            <div className='map-viewer-header'>
              <span className='map-viewer-title'>{t('map.title')}</span>
              <button
                className='map-viewer-close'
                onClick={() => setOpen(false)}
                aria-label={t('map.close')}
              >
                ×
              </button>
            </div>

            <div className='map-viewer-tabs' role='tablist'>
              {MAPS.map((m, i) => (
                <button
                  key={m.file}
                  role='tab'
                  aria-selected={activeTab === i}
                  className={`map-tab ${activeTab === i ? 'map-tab--active' : ''}`}
                  onClick={() => setActiveTab(i)}
                >
                  {m.translatable ? t(m.label) : m.label}
                </button>
              ))}
            </div>

            <div className='map-viewer-image-area'>
              <img
                key={MAPS[activeTab].file}
                src={`${API_BASE}/maps/${MAPS[activeTab].file}`}
                alt={t('map.image_alt', {
                  label: MAPS[activeTab].translatable
                    ? t(MAPS[activeTab].label)
                    : MAPS[activeTab].label,
                })}
                className='map-viewer-image'
                draggable={false}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
