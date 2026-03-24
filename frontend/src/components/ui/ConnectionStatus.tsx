import { useGameStore } from '../../store/gameStore';

const LABELS = {
  disconnected: 'Disconnected',
  connecting: 'Connecting...',
  connected: 'Connected',
  reconnecting: 'Reconnecting...',
} as const;

export function ConnectionStatus() {
  const status = useGameStore((state) => state.connectionStatus);

  return (
    <div className={`connection-status ${status}`}>
      <span className='dot' />
      {LABELS[status]}
    </div>
  );
}
