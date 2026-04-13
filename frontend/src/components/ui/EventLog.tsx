import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { useGameStore } from '../../store/gameStore';

export function EventLog() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(true);
  const events = useGameStore((state) => state.eventLog);

  const list = useMemo(() => events.slice(-12).reverse(), [events]);

  return (
    <aside className={`event-log ${open ? 'open' : 'closed'}`}>
      <button
        type='button'
        className='event-toggle'
        onClick={() => setOpen((current) => !current)}
      >
        {open ? t('events.hide') : t('events.show')}
      </button>
      {open && (
        <ul>
          {list.length === 0 && <li>{t('events.empty')}</li>}
          {list.map((event, index) => (
            <li key={`${event.event}-${index}`}>
              <strong>{event.event}</strong>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
