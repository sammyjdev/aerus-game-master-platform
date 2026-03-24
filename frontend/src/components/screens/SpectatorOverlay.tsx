import { useGameStore } from '../../store/gameStore';

interface SpectatorOverlayProps {
  readonly onCreateCharacter: () => void;
}

export function SpectatorOverlay({ onCreateCharacter }: SpectatorOverlayProps) {
  const players = useGameStore((state) => state.gameState.other_players);

  return (
    <div className='spectator-overlay'>
      <span className='spectator-badge'>SPECTATOR</span>
      <aside>
        <h3>Create New Character</h3>
        <button type='button' onClick={onCreateCharacter}>
          Go to creation
        </button>
        <h4>Other players</h4>
        <ul>
          {players.map((player) => (
            <li key={player.player_id}>
              {player.name} • HP {player.current_hp}/{player.max_hp}
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
