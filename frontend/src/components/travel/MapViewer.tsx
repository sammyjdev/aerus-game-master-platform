import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const MAPS = [
  { label: 'Mundo',    file: 'Aerus_Mapa_Mundi.png' },
  { label: 'Myr',      file: 'Aerus_IslandOfMyr_Map.png' },
  { label: 'Valdoria', file: 'Areus_Valdoria_Map.png' },
  { label: 'Shaleth',  file: 'Aerus_Shaleth_Map.png' },
  { label: 'Estravar', file: 'Aerus_Estravar_Map.png' },
  { label: 'Khorrath', file: 'Aerus_Khorrath_Map.png' },
  { label: 'Veth',     file: 'Aerus_Veth_Map.png' },
]

export function MapViewer() {
  const [open, setOpen] = useState(false)
  const [activeTab, setActiveTab] = useState(0)

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open])

  return (
    <>
      <button
        className='map-viewer-toggle'
        onClick={() => setOpen((v) => !v)}
        title='Ver mapas de Aerus'
        aria-label='Abrir visualizador de mapas'
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
            aria-label='Mapas de Aerus'
          >
            <div className='map-viewer-header'>
              <span className='map-viewer-title'>Mapas de Aerus</span>
              <button
                className='map-viewer-close'
                onClick={() => setOpen(false)}
                aria-label='Fechar'
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
                  {m.label}
                </button>
              ))}
            </div>

            <div className='map-viewer-image-area'>
              <img
                key={MAPS[activeTab].file}
                src={`${API_BASE}/maps/${MAPS[activeTab].file}`}
                alt={`Mapa: ${MAPS[activeTab].label}`}
                className='map-viewer-image'
                draggable={false}
              />
            </div>
          </div>
        </div>
      )}
    </>
  )
}
