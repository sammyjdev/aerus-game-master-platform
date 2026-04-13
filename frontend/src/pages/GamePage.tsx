import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  ActionInput,
  ByokSettings,
  CampfireScreen,
  CharacterSheet,
  CombatOrder,
  ConnectionStatus,
  DiceRoller,
  EventLog,
  IsekaiIntro,
  MapViewer,
  ManualDiceRoller,
  NarrativePanel,
  SpectatorOverlay,
  TravelTracker,
  VolumeSettings,
} from '../features/game';
import { DebugPanel } from '../components/ui/DebugPanel';
import { logClient } from '../debug/logger';
import { useAudio } from '../hooks/useAudio';
import { useTokenRefresh } from '../hooks/useTokenRefresh';
import { useWebSocket } from '../hooks/useWebSocket';
import { useGameStore } from '../store/gameStore';

export function GamePage() {
  const navigate = useNavigate();
  const token = useGameStore((state) => state.token);
  const gameState = useGameStore((state) => state.gameState);
  const isekaiEvent = useGameStore((state) => state.isekaiEvent);
  const setIsekaiEvent = useGameStore((state) => state.setIsekaiEvent);
  const setPendingDiceRoll = useGameStore((state) => state.setPendingDiceRoll);
  const [introDone, setIntroDone] = useState(false);
  const connectionStatus = useGameStore((state) => state.connectionStatus);

  useTokenRefresh();

  const { sendAction } = useWebSocket(token);
  const { startIdleMusic, stopIdleMusic } = useAudio();

  // Start idle background music when connected and not streaming
  useEffect(() => {
    const idle = connectionStatus === 'connected' && !gameState.is_streaming;
    if (idle) {
      startIdleMusic();
      logClient('debug', 'audio', 'Idle music started', { connectionStatus });
    } else if (gameState.is_streaming) {
      stopIdleMusic();
      logClient('debug', 'audio', 'Idle music paused during streaming', {
        connectionStatus,
      });
    }
  }, [connectionStatus, gameState.is_streaming, startIdleMusic, stopIdleMusic]);

  useEffect(() => {
    if (!token) {
      logClient('warn', 'game', 'Missing token; redirecting to login');
      navigate('/');
    }
  }, [navigate, token]);

  useEffect(() => {
    logClient('info', 'game', 'GamePage mounted', {
      player: gameState.current_player.name,
      status: gameState.current_player.status,
      connectionStatus,
    });
  }, [
    connectionStatus,
    gameState.current_player.name,
    gameState.current_player.status,
  ]);

  const showIntro = useMemo(
    () => Boolean(isekaiEvent && !introDone),
    [introDone, isekaiEvent],
  );
  const isSpectator = gameState.current_player.status === 'dead';
  const isCampfire = gameState.world_state.campaign_paused;

  return (
    <main className='game-page'>
      <video
        className='game-bg-video'
        src='/game-bg.mp4'
        autoPlay
        loop
        muted
        playsInline
      />

      {/* ── Left sidebar: events, status, travel, map ── */}
      <aside className='sidebar-left'>
        <EventLog />
        <ConnectionStatus />
        <TravelTracker />
        <MapViewer />
      </aside>

      {/* ── Center: narrative + action input ── */}
      <div className='center-col'>
        <NarrativePanel />
        <ActionInput onSend={sendAction} />
      </div>

      {/* ── Right sidebar: combat, character sheet, controls ── */}
      <aside className='sidebar-right'>
        <div className='sidebar-right-scroll'>
          <CombatOrder />
          <CharacterSheet />
        </div>
        <div className='controls-tray'>
          <ByokSettings token={token} />
          <VolumeSettings />
          <DebugPanel />
        </div>
      </aside>

      {gameState.pending_dice_roll && (
        <DiceRoller
          roll={gameState.pending_dice_roll}
          onDone={() => setPendingDiceRoll(null)}
        />
      )}

      {gameState.pending_manual_roll && (
        <ManualDiceRoller
          request={gameState.pending_manual_roll}
          resolution={gameState.manual_roll_resolution}
        />
      )}

      {isCampfire && <CampfireScreen />}
      {isSpectator && (
        <SpectatorOverlay onCreateCharacter={() => navigate('/character')} />
      )}

      {showIntro && isekaiEvent && (
        <IsekaiIntro
          narrative={isekaiEvent.narrative}
          secretObjective={isekaiEvent.secret_objective}
          onEnter={() => {
            logClient('info', 'isekai', 'Isekai intro completed by player', {
              faction: isekaiEvent.faction,
            });
            setIntroDone(true);
            setIsekaiEvent(null);
          }}
        />
      )}
    </main>
  );
}
