import { useEffect, useState } from 'react'

import {
  adminGenerateInvite,
  adminGetPlayers,
  adminPauseCampaign,
  adminReloadConfig,
  type AdminPlayer,
} from '../api/http'

export function AdminPage() {
  const [adminSecret, setAdminSecret] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [players, setPlayers] = useState<AdminPlayer[]>([])
  const [paused, setPaused] = useState(false)
  const [inviteCode, setInviteCode] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)

  function showStatus(msg: string) {
    setStatusMsg(msg)
    setTimeout(() => setStatusMsg(null), 3000)
  }

  async function handleAuth() {
    setLoading(true)
    setError(null)
    try {
      const data = await adminGetPlayers(adminSecret)
      setPlayers(data)
      setAuthenticated(true)
    } catch {
      setError('Invalid admin secret or server unreachable.')
    } finally {
      setLoading(false)
    }
  }

  async function refreshPlayers() {
    try {
      const data = await adminGetPlayers(adminSecret)
      setPlayers(data)
    } catch {
      setError('Failed to refresh player list.')
    }
  }

  async function handlePauseToggle() {
    const newPaused = !paused
    try {
      await adminPauseCampaign(adminSecret, newPaused)
      setPaused(newPaused)
      showStatus(newPaused ? 'Campaign paused.' : 'Campaign resumed.')
    } catch {
      setError('Failed to change campaign state.')
    }
  }

  async function handleGenerateInvite() {
    try {
      const data = await adminGenerateInvite(adminSecret)
      setInviteCode(data.invite_code)
    } catch {
      setError('Failed to generate invite.')
    }
  }

  async function handleReloadConfig() {
    try {
      await adminReloadConfig(adminSecret)
      showStatus('Configuration reloaded.')
    } catch {
      setError('Failed to reload config.')
    }
  }

  useEffect(() => {
    if (!authenticated) return
    const interval = setInterval(refreshPlayers, 10_000)
    return () => clearInterval(interval)
  }, [authenticated, adminSecret])

  if (!authenticated) {
    return (
      <main className="auth-page">
        <div className="auth-card">
          <h1>GM Admin</h1>
          <p style={{ color: '#aaa', marginBottom: '1rem' }}>Enter admin secret to access dashboard</p>
          {error && <p className="error-msg">{error}</p>}
          <input
            type="password"
            placeholder="Admin secret"
            value={adminSecret}
            onChange={(e) => setAdminSecret(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAuth()}
            className="text-input"
          />
          <button onClick={handleAuth} disabled={loading || !adminSecret} className="btn-primary">
            {loading ? 'Authenticating...' : 'Access Dashboard'}
          </button>
        </div>
      </main>
    )
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0 }}>GM Admin Dashboard</h1>
        <span style={{ color: '#888', fontSize: '0.85rem' }}>Auto-refreshes every 10s</span>
      </header>

      {statusMsg && (
        <div style={{ background: '#1a3a1a', border: '1px solid #3a6a3a', padding: '0.5rem 1rem', marginBottom: '1rem', borderRadius: '4px' }}>
          {statusMsg}
        </div>
      )}
      {error && (
        <div style={{ background: '#3a1a1a', border: '1px solid #6a3a3a', padding: '0.5rem 1rem', marginBottom: '1rem', borderRadius: '4px' }}>
          {error}
          <button onClick={() => setError(null)} style={{ marginLeft: '1rem', background: 'none', border: 'none', color: '#aaa', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Controls */}
      <section style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
        <button
          onClick={handlePauseToggle}
          className={paused ? 'btn-secondary' : 'btn-primary'}
          style={{ minWidth: '140px' }}
        >
          {paused ? 'Resume Campaign' : 'Pause Campaign'}
        </button>
        <button onClick={handleGenerateInvite} className="btn-secondary">
          Generate Invite
        </button>
        <button onClick={handleReloadConfig} className="btn-secondary">
          Reload Config
        </button>
        <button onClick={refreshPlayers} className="btn-secondary">
          Refresh Players
        </button>
      </section>

      {/* Invite code display */}
      {inviteCode && (
        <section style={{ background: '#111', border: '1px solid #333', padding: '1rem', marginBottom: '2rem', borderRadius: '4px' }}>
          <p style={{ margin: 0 }}>
            <strong>Invite Code:</strong>{' '}
            <code style={{ background: '#222', padding: '0.2rem 0.5rem', borderRadius: '3px', userSelect: 'all' }}>
              {inviteCode}
            </code>
            <button
              onClick={() => { navigator.clipboard.writeText(inviteCode); showStatus('Copied!') }}
              style={{ marginLeft: '0.75rem', background: 'none', border: '1px solid #444', color: '#ccc', cursor: 'pointer', padding: '0.2rem 0.5rem', borderRadius: '3px' }}
            >
              Copy
            </button>
          </p>
        </section>
      )}

      {/* Players table */}
      <section>
        <h2 style={{ marginBottom: '0.75rem' }}>Players ({players.length})</h2>
        {players.length === 0 ? (
          <p style={{ color: '#666' }}>No players registered.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #333', color: '#888' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem' }}>Name</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem' }}>Class</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem' }}>Faction</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem' }}>Level</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem' }}>HP</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {players.map((p) => (
                  <tr key={p.player_id} style={{ borderBottom: '1px solid #222' }}>
                    <td style={{ padding: '0.5rem' }}>
                      <span style={{ fontWeight: 500 }}>{p.name ?? p.username}</span>
                      <span style={{ color: '#555', fontSize: '0.8rem', marginLeft: '0.4rem' }}>@{p.username}</span>
                    </td>
                    <td style={{ padding: '0.5rem', color: '#aaa' }}>{p.inferred_class ?? '—'}</td>
                    <td style={{ padding: '0.5rem', color: '#aaa' }}>{p.faction ?? '—'}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>{p.level}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      <span style={{ color: p.current_hp < p.max_hp * 0.3 ? '#c44' : '#8c8' }}>
                        {p.current_hp}/{p.max_hp}
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      <span style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '3px',
                        fontSize: '0.8rem',
                        background: p.is_alive ? '#1a2e1a' : '#2e1a1a',
                        color: p.is_alive ? '#6a6' : '#a66',
                      }}>
                        {p.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}
