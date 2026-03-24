import { motion } from 'framer-motion';

import { useGameStore } from '../../store/gameStore';

const STATUS_LABEL: Record<string, string> = {
  alive: 'alive',
  dead: 'dead',
  spectator: 'spectator',
}

export function CampfireScreen() {
  const currentPlayer = useGameStore((state) => state.gameState.current_player);
  const otherPlayers = useGameStore((state) => state.gameState.other_players);
  const players = [currentPlayer, ...otherPlayers];

  return (
    <div className='campfire-screen'>
      <video
        className='campfire-video'
        src='/campfire.mp4'
        autoPlay
        loop
        muted
        playsInline
      />

      <motion.h3
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.5 }}
      >
        The Game Master is preparing the next chapter...
      </motion.h3>

      <motion.ul
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.7, duration: 0.4 }}
      >
        {players
          .filter((p) => p.name)
          .map((player) => (
            <li key={player.player_id || player.name}>
              <span className={`status-dot ${player.status}`} />
              {player.name}
              <span className='status-label'>
                {STATUS_LABEL[player.status] ?? player.status}
              </span>
            </li>
          ))}
      </motion.ul>
    </div>
  )
}
