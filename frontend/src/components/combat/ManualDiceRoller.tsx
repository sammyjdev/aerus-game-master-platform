import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { submitManualDiceRoll } from '../../api/http';
import { useGameStore } from '../../store/gameStore';
import type {
  ManualDiceRequestEvent,
  ManualDiceResolvedEvent,
} from '../../types';

interface ManualDiceRollerProps {
  readonly request: ManualDiceRequestEvent;
  readonly resolution: ManualDiceResolvedEvent | null;
}

export function ManualDiceRoller({
  request,
  resolution,
}: ManualDiceRollerProps) {
  const token = useGameStore((state) => state.token);
  const setPendingManualRoll = useGameStore(
    (state) => state.setPendingManualRoll,
  );
  const setManualRollResolution = useGameStore(
    (state) => state.setManualRollResolution,
  );

  const [rolling, setRolling] = useState(false);
  const [rolledValue, setRolledValue] = useState<number | null>(null);
  const [argument, setArgument] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { t } = useTranslation();
  const rollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const rollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const interval = rollIntervalRef;
    const timeout = rollTimeoutRef;
    return () => {
      if (interval.current) globalThis.clearInterval(interval.current);
      if (timeout.current) globalThis.clearTimeout(timeout.current);
    };
  }, []);

  const finalResolution = useMemo(() => {
    if (!resolution) return null;
    if (resolution.roll_id !== request.roll_id) return null;
    return resolution;
  }, [request.roll_id, resolution]);

  const closeResolved = () => {
    setPendingManualRoll(null);
    setManualRollResolution(null);
  };

  // ESC closes when resolved
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && finalResolution) closeResolved();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [finalResolution]);

  const startRoll = () => {
    setError(null);
    setRolling(true);
    rollIntervalRef.current = globalThis.setInterval(() => {
      setRolledValue(Math.floor(Math.random() * 20) + 1);
    }, 80);

    rollTimeoutRef.current = globalThis.setTimeout(() => {
      if (rollIntervalRef.current)
        globalThis.clearInterval(rollIntervalRef.current);
      rollIntervalRef.current = null;
      setRolledValue(Math.floor(Math.random() * 20) + 1);
      setRolling(false);
    }, 1800);
  };

  const submit = async () => {
    if (!token || rolledValue === null || submitted) return;
    try {
      await submitManualDiceRoll(token, {
        roll_id: request.roll_id,
        initial_roll: rolledValue,
        initial_result: rolledValue,
        argument,
      });
      setSubmitted(true);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit roll');
    }
  };

  return (
    <div
      className='dice-overlay'
      onClick={finalResolution ? closeResolved : undefined}
    >
      <div
        className='dice-card manual-dice-card'
        role='dialog'
        aria-modal='true'
        aria-labelledby='manual-dice-title'
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id='manual-dice-title'>{t('dice.gm_roll_title')}</h3>
        <p>
          <strong>{request.roll_type.toUpperCase()}</strong> • DC {request.dc}
        </p>
        <p className='muted'>{request.description}</p>

        <div className={`manual-dice-value${rolling ? ' rolling' : ''}`}>
          {rolledValue ?? '🎲'}
        </div>

        {rolledValue === null && (
          <button
            type='button'
            onClick={startRoll}
            disabled={rolling}
            autoFocus
          >
            {rolling ? t('dice.rolling') : t('dice.roll_d20')}
          </button>
        )}

        {rolledValue !== null && !submitted && (
          <>
            <label>
              <span>{t('dice.circumstance_placeholder')}</span>
              <textarea
                value={argument}
                onChange={(event) => setArgument(event.target.value)}
                maxLength={300}
                placeholder={t('dice.circumstance_hint')}
              />
            </label>
            <button type='button' onClick={submit} disabled={rolling}>
              {t('dice.submit_roll')}
            </button>
          </>
        )}

        {submitted && !finalResolution && (
          <p className='muted'>{t('dice.waiting_gm')}</p>
        )}

        {finalResolution && (
          <div className='manual-resolution'>
            <h4>
              {t('dice.gm_decision')}
              {finalResolution.verdict}
            </h4>
            <p>
              {t('dice.applied_bonus')}
              {finalResolution.circumstance_bonus}
              {t('dice.final_result')}
              {finalResolution.final_result ?? t('dice.reroll_requested')}
            </p>
            <p>{finalResolution.explanation || t('dice.no_notes')}</p>
            {finalResolution.verdict === 'reroll_requested' ? (
              <button
                type='button'
                onClick={() => {
                  setRolledValue(null);
                  setArgument('');
                  setSubmitted(false);
                  setManualRollResolution(null);
                }}
              >
                {t('dice.reroll')}
              </button>
            ) : (
              <button type='button' onClick={closeResolved} autoFocus>
                {t('dice.close')}
              </button>
            )}
          </div>
        )}

        {error && <p className='error'>{error}</p>}
      </div>
    </div>
  );
}
