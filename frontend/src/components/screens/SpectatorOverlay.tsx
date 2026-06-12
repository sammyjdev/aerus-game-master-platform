import { useGameStore } from '../../store/gameStore';
import { useTranslation } from 'react-i18next';

interface SpectatorOverlayProps {
  readonly onCreateCharacter: () => void;
}

export function SpectatorOverlay({ onCreateCharacter }: SpectatorOverlayProps) {
  const { t } = useTranslation();
  const players = useGameStore((state) => state.gameState.other_players);

  return (
    <div className='spectator-overlay'>
      <span className='spectator-badge'>{t('game_ui.spectator.badge')}</span>
      <aside>
        <h3>{t('game_ui.spectator.create_title')}</h3>
        <button type='button' onClick={onCreateCharacter}>
          {t('game_ui.spectator.go_to_creation')}
        </button>
        <h4>{t('game_ui.spectator.other_players')}</h4>
        <ul>
          {players.map((player) => (
            <li key={player.player_id}>
              {player.name} • {t('game_ui.spectator.hp')} {player.current_hp}/
              {player.max_hp}
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
