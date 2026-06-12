import { useGameStore } from '../../store/gameStore';
import { useTranslation } from 'react-i18next';

export function ConnectionStatus() {
  const { t } = useTranslation();
  const status = useGameStore((state) => state.connectionStatus);
  const labels = {
    disconnected: t('game_ui.connection.disconnected'),
    connecting: t('game_ui.connection.connecting'),
    connected: t('game_ui.connection.connected'),
    reconnecting: t('game_ui.connection.reconnecting'),
  } as const;

  return (
    <div className={`connection-status ${status}`}>
      <span className='dot' />
      {labels[status]}
    </div>
  );
}
