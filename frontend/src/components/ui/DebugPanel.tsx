import { useMemo, useState } from 'react';

import { getDebugStateSnapshot } from '../../api/http';
import { setClientDebugEnabled } from '../../debug/logger';
import { useGameStore } from '../../store/gameStore';
import type { DebugStateSnapshot } from '../../types';

function normalizeCampaignPaused(value: string | null) {
  if (value === null) {
    return null;
  }
  const text = value.trim().toLowerCase();
  if (text === '1' || text === 'true' || text === 'yes' || text === 'on') {
    return true;
  }
  if (text === '0' || text === 'false' || text === 'no' || text === 'off') {
    return false;
  }
  return null;
}

function buildStateDiff(
  snapshot: DebugStateSnapshot,
  localState: ReturnType<typeof useGameStore.getState>['gameState'],
) {
  const diffs: string[] = [];
  if (snapshot.player.level !== localState.current_player.level) {
    diffs.push(
      `level: backend=${snapshot.player.level} frontend=${localState.current_player.level}`,
    );
  }
  if (
    snapshot.player.inferred_class !== localState.current_player.inferred_class
  ) {
    diffs.push(
      `class: backend=${snapshot.player.inferred_class} frontend=${localState.current_player.inferred_class}`,
    );
  }
  if (snapshot.player.current_hp !== localState.current_player.current_hp) {
    diffs.push(
      `hp: backend=${snapshot.player.current_hp} frontend=${localState.current_player.current_hp}`,
    );
  }
  if (snapshot.player.current_mp !== localState.current_player.current_mp) {
    diffs.push(
      `mp: backend=${snapshot.player.current_mp} frontend=${localState.current_player.current_mp}`,
    );
  }
  if (
    snapshot.player.current_stamina !==
    localState.current_player.current_stamina
  ) {
    diffs.push(
      `stamina: backend=${snapshot.player.current_stamina} frontend=${localState.current_player.current_stamina}`,
    );
  }
  if (snapshot.world_state.current_turn !== localState.turn_number) {
    diffs.push(
      `turn: backend=${snapshot.world_state.current_turn} frontend=${localState.turn_number}`,
    );
  }
  const backendCampaignPaused = normalizeCampaignPaused(
    snapshot.world_state.campaign_paused,
  );
  if (
    backendCampaignPaused !== null &&
    backendCampaignPaused !== localState.world_state.campaign_paused
  ) {
    diffs.push(
      `campaign_paused: backend=${backendCampaignPaused} frontend=${localState.world_state.campaign_paused}`,
    );
  }
  return diffs;
}

export function DebugPanel() {
  const [open, setOpen] = useState(false);
  const [loadingSnapshot, setLoadingSnapshot] = useState(false);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<DebugStateSnapshot | null>(null);
  const debugEnabled = useGameStore((state) => state.debugEnabled);
  const debugEntries = useGameStore((state) => state.debugEntries);
  const clearDebugEntries = useGameStore((state) => state.clearDebugEntries);
  const connectionStatus = useGameStore((state) => state.connectionStatus);
  const currentPlayer = useGameStore((state) => state.gameState.current_player);
  const gameState = useGameStore((state) => state.gameState);
  const turnNumber = useGameStore((state) => state.gameState.turn_number);
  const token = useGameStore((state) => state.token);

  const visibleEntries = useMemo(
    () => [...debugEntries].reverse().slice(0, 80),
    [debugEntries],
  );

  const stateDiff = useMemo(
    () => (snapshot ? buildStateDiff(snapshot, gameState) : []),
    [gameState, snapshot],
  );

  async function refreshSnapshot() {
    if (!token) {
      setSnapshotError('No authenticated token available to fetch the snapshot.');
      return;
    }
    setLoadingSnapshot(true);
    setSnapshotError(null);
    try {
      const data = await getDebugStateSnapshot(token);
      setSnapshot(data);
    } catch (error) {
      setSnapshotError(
        error instanceof Error ? error.message : 'Failed to load snapshot.',
      );
    } finally {
      setLoadingSnapshot(false);
    }
  }

  return (
    <div className={`debug-panel-shell ${open ? 'open' : ''}`}>
      <button
        type='button'
        className='debug-toggle'
        onClick={() => setOpen((value) => !value)}
      >
        Debug
      </button>

      {open && (
        <section className='debug-panel panel'>
          <header className='debug-panel-header'>
            <div>
              <strong>Debug Console</strong>
              <div className='muted'>
                connection: {connectionStatus} | player:{' '}
                {currentPlayer.name || 'anon'} | turn: {turnNumber}
              </div>
            </div>
            <div className='debug-panel-actions'>
              <button
                type='button'
                className={debugEnabled ? 'active' : ''}
                onClick={() => setClientDebugEnabled(!debugEnabled)}
              >
                {debugEnabled ? 'Debug on' : 'Debug off'}
              </button>
              <button
                type='button'
                disabled={loadingSnapshot}
                onClick={() => void refreshSnapshot()}
              >
                {loadingSnapshot ? 'Loading...' : 'Snapshot'}
              </button>
              <button type='button' onClick={() => clearDebugEntries()}>
                Clear
              </button>
            </div>
          </header>

          <section className='debug-state-compare'>
            <strong>Backend vs frontend comparison</strong>
            {snapshotError && <div className='error'>{snapshotError}</div>}
            {!snapshot && !snapshotError && (
              <div className='muted'>
                Click Snapshot to load backend state.
              </div>
            )}
            {snapshot && (
              <>
                <div className='debug-state-grid'>
                  <div>
                    <div className='muted'>Backend</div>
                    <div>turn: {snapshot.world_state.current_turn}</div>
                    <div>class: {snapshot.player.inferred_class || 'n/a'}</div>
                    <div>
                      hp/mp/st: {snapshot.player.current_hp}/
                      {snapshot.player.current_mp}/
                      {snapshot.player.current_stamina}
                    </div>
                    <div>connected: {snapshot.runtime.connected_players}</div>
                  </div>
                  <div>
                    <div className='muted'>Frontend</div>
                    <div>turn: {gameState.turn_number}</div>
                    <div>
                      class: {gameState.current_player.inferred_class || 'n/a'}
                    </div>
                    <div>
                      hp/mp/st: {gameState.current_player.current_hp}/
                      {gameState.current_player.current_mp}/
                      {gameState.current_player.current_stamina}
                    </div>
                    <div>connection: {connectionStatus}</div>
                  </div>
                </div>

                {stateDiff.length === 0 ? (
                  <div className='save-ok'>
                    Local state is consistent with the backend snapshot.
                  </div>
                ) : (
                  <ul className='debug-diff-list'>
                    {stateDiff.map((diff) => (
                      <li key={diff}>{diff}</li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </section>

          <div className='debug-log-list'>
            {visibleEntries.length === 0 && (
              <div className='muted'>No logs captured.</div>
            )}
            {visibleEntries.map((entry) => (
              <article
                key={entry.id}
                className={`debug-log-entry ${entry.level}`}
              >
                <div className='debug-log-meta'>
                  <span>{new Date(entry.timestamp).toLocaleTimeString()}</span>
                  <span>{entry.level}</span>
                  <span>{entry.scope}</span>
                </div>
                <div className='debug-log-message'>{entry.message}</div>
                {entry.details !== undefined && (
                  <pre>{JSON.stringify(entry.details, null, 2)}</pre>
                )}
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
