import { useEffect, useRef, useState } from 'react';

import { useGameStore } from '../../store/gameStore';

interface ActionInputProps {
  readonly onSend: (text: string) => void;
}

export function ActionInput({ onSend }: ActionInputProps) {
  const [value, setValue] = useState('');
  const [locked, setLocked] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const macros = useGameStore((state) => state.gameState.current_player.macros);
  const inputRef = useRef<HTMLInputElement>(null);
  const lockTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // History of sent actions for up/down navigation (max 50 entries)
  const historyRef = useRef<string[]>([]);
  const historyIndexRef = useRef<number>(-1);
  const draftRef = useRef<string>('');

  useEffect(() => {
    return () => {
      if (lockTimerRef.current) globalThis.clearTimeout(lockTimerRef.current);
      if (countdownRef.current) globalThis.clearInterval(countdownRef.current);
    };
  }, []);

  const submit = (event?: { preventDefault: () => void }) => {
    event?.preventDefault();
    const text = value.trim();
    if (!text || locked) return;

    const macroMatch = macros.find((macro) => macro.name === text);
    const finalText = macroMatch?.template ?? text;

    onSend(finalText);

    // Push to history (avoid consecutive duplicates)
    if (historyRef.current[0] !== text) {
      historyRef.current.unshift(text);
      if (historyRef.current.length > 50) historyRef.current.pop();
    }
    historyIndexRef.current = -1;
    draftRef.current = '';

    setValue('');
    setLocked(true);
    lockTimerRef.current = globalThis.setTimeout(() => {
      setLocked(false);
      inputRef.current?.focus();
    }, 500);

    if (countdownRef.current) globalThis.clearInterval(countdownRef.current);
    let tick = 3;
    setCountdown(tick);
    countdownRef.current = globalThis.setInterval(() => {
      tick -= 1;
      setCountdown(tick);
      if (tick <= 0) {
        globalThis.clearInterval(countdownRef.current!);
        countdownRef.current = null;
        setCountdown(null);
      }
    }, 1000);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      submit();
      return;
    }

    if (e.key === 'ArrowUp' && historyRef.current.length > 0) {
      e.preventDefault();
      if (historyIndexRef.current === -1) {
        draftRef.current = value;
      }
      const nextIndex = Math.min(historyIndexRef.current + 1, historyRef.current.length - 1);
      historyIndexRef.current = nextIndex;
      setValue(historyRef.current[nextIndex]);
      return;
    }

    if (e.key === 'ArrowDown' && historyIndexRef.current !== -1) {
      e.preventDefault();
      const nextIndex = historyIndexRef.current - 1;
      historyIndexRef.current = nextIndex;
      setValue(nextIndex === -1 ? draftRef.current : historyRef.current[nextIndex]);
    }
  };

  return (
    <form className='action-input' onSubmit={submit}>
      <input
        ref={inputRef}
        value={value}
        maxLength={500}
        onChange={(e) => {
          setValue(e.target.value);
          historyIndexRef.current = -1;
        }}
        onKeyDown={onKeyDown}
        placeholder='Action... (↑↓ history · Ctrl+Enter to send)'
        aria-label='Player action'
        aria-describedby={countdown !== null ? 'action-countdown' : undefined}
        disabled={locked}
      />
      <button type='submit' disabled={locked || value.trim().length === 0}>
        Send
      </button>
      {countdown !== null && (
        <p
          id='action-countdown'
          className='action-input-countdown'
          role='status'
          aria-live='polite'
        >
          Waiting for other players... ({countdown}s)
        </p>
      )}
    </form>
  );
}
