import { useGameStore } from '../../store/gameStore';

export function CombatOrder() {
  const currentPlayer = useGameStore((state) => state.gameState.current_player);
  const otherPlayers = useGameStore((state) => state.gameState.other_players);
  const players = [currentPlayer, ...otherPlayers];

  return (
    <aside className='combat-order'>
      <h3>Ordem de Combate</h3>
      <ol>
        {players.map((player) => (
          <li key={player.player_id || player.name}>
            {player.name || 'Jogador'}
          </li>
        ))}
      </ol>
    </aside>
  );
}
