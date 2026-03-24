import { useEffect } from 'react';

import type { DiceRollEvent } from '../../types';

interface DiceRollerProps {
  readonly roll: DiceRollEvent;
  readonly onDone: () => void;
}

export function DiceRoller({ roll, onDone }: DiceRollerProps) {
  useEffect(() => {
    const timeout = globalThis.setTimeout(onDone, 2500);
    return () => globalThis.clearTimeout(timeout);
  }, [onDone]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDone();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onDone]);

  return (
    <div className='dice-overlay'>
      <div
        className={`dice-card dice-card-enter ${roll.is_critical ? 'critical' : ''} ${roll.is_fumble ? 'fumble' : ''}`}
        role='alert'
      >
        <button
          type='button'
          className='dice-close'
          onClick={onDone}
          aria-label='Fechar'
        >
          ×
        </button>
        <div className='dice-value dice-value-spin'>
          {roll.result}
        </div>
        <p>{`${roll.player} - ${roll.purpose}`}</p>
      </div>
    </div>
  );
}
