import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  adminGenerateInvite,
  adminGetPlayerDetail,
  adminGetPlayers,
  adminPauseCampaign,
  adminReloadConfig,
  adminUpdatePlayer,
  type AdminPlayer,
  type AdminPlayerDetail,
  type AdminPlayerUpdatePayload,
} from '../api/http'
import { LanguageSwitcher } from '../components/ui/LanguageSwitcher'

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

export function AdminPage() {
  const { t } = useTranslation()
  const [adminSecret, setAdminSecret] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [players, setPlayers] = useState<AdminPlayer[]>([])
  const [paused, setPaused] = useState(false)
  const [inviteCode, setInviteCode] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null)
  const [editorValue, setEditorValue] = useState('')

  const draftPlayer = useMemo(() => {
    if (!editorValue.trim()) return null
    try {
      return JSON.parse(editorValue) as AdminPlayerDetail
    } catch {
      return null
    }
  }, [editorValue])

  function showStatus(msg: string) {
    setStatusMsg(msg)
    setTimeout(() => setStatusMsg(null), 3000)
  }

  async function loadPlayer(playerId: string) {
    setDetailLoading(true)
    setError(null)
    try {
      const data = await adminGetPlayerDetail(adminSecret, playerId)
      setSelectedPlayerId(playerId)
      setEditorValue(formatJson(data.player))
    } catch {
      setError('Falha ao carregar os dados completos do personagem.')
    } finally {
      setDetailLoading(false)
    }
  }

  function updateEditorField(field: string, value: unknown) {
    const base = draftPlayer ?? {}
    const next = { ...base, [field]: value }
    setEditorValue(formatJson(next))
  }

  async function handleAuth() {
    setLoading(true)
    setError(null)
    try {
      const data = await adminGetPlayers(adminSecret)
      setPlayers(data)
      setAuthenticated(true)
      if (data[0]?.player_id) {
        await loadPlayer(data[0].player_id)
      }
    } catch {
      setError(t('admin.errors.invalid_secret'))
    } finally {
      setLoading(false)
    }
  }

  async function refreshPlayers() {
    try {
      const data = await adminGetPlayers(adminSecret)
      setPlayers(data)
    } catch {
      setError(t('admin.errors.refresh_failed'))
    }
  }

  async function handlePauseToggle() {
    const newPaused = !paused
    try {
      const result = await adminPauseCampaign(adminSecret, newPaused)
      setPaused(result.campaign_paused)
      showStatus(
        result.campaign_paused ? t('admin.status.paused') : t('admin.status.resumed'),
      )
    } catch {
      setError(t('admin.errors.toggle_failed'))
    }
  }

  async function handleGenerateInvite() {
    try {
      const data = await adminGenerateInvite(adminSecret)
      setInviteCode(data.invite_code)
    } catch {
      setError(t('admin.errors.invite_failed'))
    }
  }

  async function handleReloadConfig() {
    try {
      await adminReloadConfig(adminSecret)
      showStatus(t('admin.status.reloaded'))
    } catch {
      setError(t('admin.errors.reload_failed'))
    }
  }

  async function handleSavePlayer() {
    if (!selectedPlayerId) return
    if (!draftPlayer) {
      setError('JSON inválido. Corrija o editor avançado antes de salvar.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const payload = draftPlayer as AdminPlayerUpdatePayload
      const data = await adminUpdatePlayer(adminSecret, selectedPlayerId, payload)
      setEditorValue(formatJson(data.player))
      await refreshPlayers()
      showStatus('Dados do personagem atualizados com sucesso.')
    } catch {
      setError('Falha ao salvar as alterações do personagem.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!authenticated) return
    const interval = setInterval(refreshPlayers, 10_000)
    return () => clearInterval(interval)
  }, [authenticated, adminSecret])

  if (!authenticated) {
    return (
      <main className='auth-page'>
        <div className='auth-card'>
          <div className='page-tools'>
            <LanguageSwitcher />
          </div>
          <h1>{t('admin.title')}</h1>
          <p style={{ color: '#aaa', marginBottom: '1rem' }}>
            {t('admin.subtitle')}
          </p>
          {error && <p className='error-msg'>{error}</p>}
          <input
            type='password'
            placeholder={t('admin.fields.secret_placeholder')}
            value={adminSecret}
            onChange={(e) => setAdminSecret(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAuth()}
            className='text-input'
          />
          <button
            onClick={handleAuth}
            disabled={loading || !adminSecret}
            className='btn-primary'
          >
            {loading
              ? t('admin.actions.authenticating')
              : t('admin.actions.access_dashboard')}
          </button>
        </div>
      </main>
    )
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem',
          marginBottom: '1.5rem',
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>{t('admin.dashboard_title')}</h1>
          <div style={{ color: '#888', fontSize: '0.85rem' }}>
            {t('admin.autorefresh')}
          </div>
        </div>
        <LanguageSwitcher />
      </header>

      {statusMsg && (
        <div
          style={{
            background: '#1a3a1a',
            border: '1px solid #3a6a3a',
            padding: '0.5rem 1rem',
            marginBottom: '1rem',
            borderRadius: '4px',
          }}
        >
          {statusMsg}
        </div>
      )}

      {error && (
        <div
          style={{
            background: '#3a1a1a',
            border: '1px solid #6a3a3a',
            padding: '0.5rem 1rem',
            marginBottom: '1rem',
            borderRadius: '4px',
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: '1rem',
              background: 'none',
              border: 'none',
              color: '#aaa',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        </div>
      )}

      <section
        style={{
          display: 'flex',
          gap: '0.75rem',
          flexWrap: 'wrap',
          marginBottom: '1rem',
        }}
      >
        <button
          onClick={handlePauseToggle}
          className={paused ? 'btn-secondary' : 'btn-primary'}
        >
          {paused ? t('admin.actions.resume_campaign') : t('admin.actions.pause_campaign')}
        </button>
        <button onClick={handleGenerateInvite} className='btn-secondary'>
          {t('admin.actions.generate_invite')}
        </button>
        <button onClick={handleReloadConfig} className='btn-secondary'>
          {t('admin.actions.reload_config')}
        </button>
        <button onClick={refreshPlayers} className='btn-secondary'>
          {t('admin.actions.refresh_players')}
        </button>
        <button
          onClick={handleSavePlayer}
          className='btn-primary'
          disabled={loading || !selectedPlayerId}
        >
          Salvar personagem
        </button>
      </section>

      {inviteCode && (
        <section
          style={{
            background: '#111',
            border: '1px solid #333',
            padding: '1rem',
            marginBottom: '1rem',
            borderRadius: '4px',
          }}
        >
          <strong>{t('admin.invite_code')}:</strong> {inviteCode}
          <button
            onClick={() => {
              navigator.clipboard.writeText(inviteCode)
              showStatus(t('admin.status.copied'))
            }}
            style={{
              marginLeft: '0.75rem',
              background: 'none',
              border: '1px solid #444',
              color: '#ccc',
              cursor: 'pointer',
              padding: '0.2rem 0.5rem',
              borderRadius: '3px',
            }}
          >
            {t('admin.actions.copy')}
          </button>
        </section>
      )}

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 420px) 1fr',
          gap: '1rem',
          alignItems: 'start',
        }}
      >
        <aside
          style={{
            background: '#111',
            border: '1px solid #2a2a2a',
            borderRadius: '8px',
            padding: '1rem',
          }}
        >
          <h2 style={{ marginTop: 0 }}>
            {t('admin.players')} ({players.length})
          </h2>
          {players.length === 0 ? (
            <p style={{ color: '#666' }}>{t('admin.no_players')}</p>
          ) : (
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              {players.map((p) => {
                const isSelected = p.player_id === selectedPlayerId
                return (
                  <button
                    key={p.player_id}
                    onClick={() => loadPlayer(p.player_id)}
                    style={{
                      textAlign: 'left',
                      background: isSelected ? '#1f2a38' : '#181818',
                      border: isSelected ? '1px solid #4d6b99' : '1px solid #2d2d2d',
                      borderRadius: '6px',
                      color: '#ddd',
                      padding: '0.75rem',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{p.name ?? p.username}</div>
                    <div style={{ color: '#888', fontSize: '0.85rem' }}>@{p.username}</div>
                    <div style={{ color: '#aaa', fontSize: '0.85rem', marginTop: '0.35rem' }}>
                      {p.inferred_class ?? 'sem classe'} • {p.faction ?? 'sem facção'}
                    </div>
                    <div style={{ color: p.current_hp < p.max_hp * 0.3 ? '#c44' : '#8c8', marginTop: '0.35rem' }}>
                      HP {p.current_hp}/{p.max_hp} • Lv {p.level}
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </aside>

        <section
          style={{
            background: '#111',
            border: '1px solid #2a2a2a',
            borderRadius: '8px',
            padding: '1rem',
          }}
        >
          {!selectedPlayerId ? (
            <p style={{ color: '#777' }}>Selecione um personagem para editar.</p>
          ) : detailLoading ? (
            <p style={{ color: '#777' }}>Carregando dados completos...</p>
          ) : (
            <>
              <h2 style={{ marginTop: 0 }}>
                Editor completo de personagem
              </h2>
              <p style={{ color: '#888', marginTop: '-0.4rem' }}>
                Edite campos rápidos abaixo ou ajuste o JSON completo para corrigir qualquer dado persistido.
              </p>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                  gap: '0.75rem',
                  marginBottom: '1rem',
                }}
              >
                <div><strong>Lv</strong><div>{draftPlayer?.level ?? '-'}</div></div>
                <div><strong>XP</strong><div>{draftPlayer?.experience ?? '-'}</div></div>
                <div><strong>HP</strong><div>{draftPlayer?.current_hp ?? '-'}/{draftPlayer?.max_hp ?? '-'}</div></div>
                <div><strong>MP</strong><div>{draftPlayer?.current_mp ?? '-'}/{draftPlayer?.max_mp ?? '-'}</div></div>
                <div><strong>STA</strong><div>{draftPlayer?.current_stamina ?? '-'}/{draftPlayer?.max_stamina ?? '-'}</div></div>
                <div><strong>Status</strong><div>{draftPlayer?.status ?? '-'}</div></div>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '0.75rem',
                  marginBottom: '1rem',
                }}
              >
                <label>
                  <div>Nome</div>
                  <input className='text-input' value={draftPlayer?.name ?? ''} onChange={(e) => updateEditorField('name', e.target.value)} />
                </label>
                <label>
                  <div>Usuário</div>
                  <input className='text-input' value={draftPlayer?.username ?? ''} onChange={(e) => updateEditorField('username', e.target.value)} />
                </label>
                <label>
                  <div>Classe</div>
                  <input className='text-input' value={draftPlayer?.inferred_class ?? ''} onChange={(e) => updateEditorField('inferred_class', e.target.value)} />
                </label>
                <label>
                  <div>Facção</div>
                  <input className='text-input' value={draftPlayer?.faction ?? ''} onChange={(e) => updateEditorField('faction', e.target.value)} />
                </label>
                <label>
                  <div>Raça</div>
                  <input className='text-input' value={draftPlayer?.race ?? ''} onChange={(e) => updateEditorField('race', e.target.value)} />
                </label>
                <label>
                  <div>Subraça</div>
                  <input className='text-input' value={draftPlayer?.subrace ?? ''} onChange={(e) => updateEditorField('subrace', e.target.value)} />
                </label>
                <label>
                  <div>Status</div>
                  <input className='text-input' value={draftPlayer?.status ?? ''} onChange={(e) => updateEditorField('status', e.target.value)} />
                </label>
                <label>
                  <div>Selo</div>
                  <input className='text-input' value={draftPlayer?.flame_seal ?? ''} onChange={(e) => updateEditorField('flame_seal', e.target.value)} />
                </label>
                <label>
                  <div>Level</div>
                  <input className='text-input' type='number' value={draftPlayer?.level ?? 1} onChange={(e) => updateEditorField('level', Number(e.target.value || 1))} />
                </label>
                <label>
                  <div>XP</div>
                  <input className='text-input' type='number' value={draftPlayer?.experience ?? 0} onChange={(e) => updateEditorField('experience', Number(e.target.value || 0))} />
                </label>
                <label>
                  <div>HP atual</div>
                  <input className='text-input' type='number' value={draftPlayer?.current_hp ?? 0} onChange={(e) => updateEditorField('current_hp', Number(e.target.value || 0))} />
                </label>
                <label>
                  <div>HP máximo</div>
                  <input className='text-input' type='number' value={draftPlayer?.max_hp ?? 1} onChange={(e) => updateEditorField('max_hp', Number(e.target.value || 1))} />
                </label>
                <label>
                  <div>MP atual</div>
                  <input className='text-input' type='number' value={draftPlayer?.current_mp ?? 0} onChange={(e) => updateEditorField('current_mp', Number(e.target.value || 0))} />
                </label>
                <label>
                  <div>MP máximo</div>
                  <input className='text-input' type='number' value={draftPlayer?.max_mp ?? 0} onChange={(e) => updateEditorField('max_mp', Number(e.target.value || 0))} />
                </label>
                <label>
                  <div>Stamina atual</div>
                  <input className='text-input' type='number' value={draftPlayer?.current_stamina ?? 0} onChange={(e) => updateEditorField('current_stamina', Number(e.target.value || 0))} />
                </label>
                <label>
                  <div>Stamina máxima</div>
                  <input className='text-input' type='number' value={draftPlayer?.max_stamina ?? 1} onChange={(e) => updateEditorField('max_stamina', Number(e.target.value || 1))} />
                </label>
              </div>

              <label style={{ display: 'block', marginBottom: '0.75rem' }}>
                <div>Backstory</div>
                <textarea
                  value={draftPlayer?.backstory ?? ''}
                  onChange={(e) => updateEditorField('backstory', e.target.value)}
                  rows={4}
                  style={{ width: '100%', background: '#181818', color: '#ddd', border: '1px solid #333', borderRadius: '6px', padding: '0.75rem' }}
                />
              </label>

              <label style={{ display: 'block', marginBottom: '1rem' }}>
                <div>Objetivo secreto</div>
                <textarea
                  value={draftPlayer?.secret_objective ?? ''}
                  onChange={(e) => updateEditorField('secret_objective', e.target.value)}
                  rows={3}
                  style={{ width: '100%', background: '#181818', color: '#ddd', border: '1px solid #333', borderRadius: '6px', padding: '0.75rem' }}
                />
              </label>

              <label style={{ display: 'block' }}>
                <div style={{ marginBottom: '0.5rem' }}>Editor JSON avançado</div>
                <textarea
                  value={editorValue}
                  onChange={(e) => setEditorValue(e.target.value)}
                  rows={24}
                  spellCheck={false}
                  style={{
                    width: '100%',
                    fontFamily: 'Consolas, monospace',
                    fontSize: '0.9rem',
                    lineHeight: 1.4,
                    background: '#0d1117',
                    color: '#d2e0ff',
                    border: '1px solid #2f3b52',
                    borderRadius: '6px',
                    padding: '0.75rem',
                  }}
                />
              </label>
            </>
          )}
        </section>
      </section>
    </main>
  )
}
