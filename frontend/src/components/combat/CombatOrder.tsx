import { useTranslation } from 'react-i18next';
import { useGameStore } from '../../store/gameStore';

export function CombatOrder() {
  const { t } = useTranslation();
  const initiativeOrder = useGameStore((state) => state.initiative_order);
  const currentActorId = useGameStore((state) => state.current_actor_id);
  const currentPlayer = useGameStore((state) => state.gameState.current_player);
  const otherPlayers = useGameStore((state) => state.gameState.other_players);

  // If no initiative order set, fall back to flat player list
  const displayOrder =
    initiativeOrder.length > 0
      ? initiativeOrder
      : [currentPlayer, ...otherPlayers].map((p) => ({
          player_id: p.player_id,
          name: p.name || t('combat.player_fallback'),
          initiative: 0,
        }));

  return (
    <aside className='combat-order'>
      <h3>{t('combat.order_title')}</h3>
      <ol>
        {displayOrder.map((entry) => {
          const isActive = entry.player_id === currentActorId;
          return (
            <li
              key={entry.player_id || entry.name}
              className={isActive ? 'active-actor' : ''}
              aria-current={isActive ? 'true' : undefined}
            >
              <span className='initiative-roll'>
                {entry.initiative > 0 ? `[${entry.initiative}]` : ''}
              </span>{' '}
              {entry.name || t('combat.player_fallback')}
              {isActive && (
                <span
                  className='turn-indicator'
                  aria-label={t('combat.current_turn')}
                >
                  {' '}
                  ◀
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </aside>
  );
}
