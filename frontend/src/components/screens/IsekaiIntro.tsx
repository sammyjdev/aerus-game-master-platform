import { memo, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';

interface IsekaiIntroProps {
  readonly narrative: string;
  readonly secretObjective: string;
  readonly onEnter: () => void;
}

const NarrativeWords = memo(function NarrativeWords({
  text,
}: Readonly<{ text: string }>) {
  const words = useMemo(() => text.split(/(\s+)/).filter(Boolean), [text]);
  let offset = 0;
  return (
    <>
      {words.map((word) => {
        const key = offset;
        offset += word.length;
        return (
          <span
            key={key}
            className='streaming-word'
            style={{
              animationDelay: `${key * 0.015}s`,
              opacity: 0,
              animationFillMode: 'forwards',
            }}
          >
            {word}
          </span>
        );
      })}
    </>
  );
});

export function IsekaiIntro({
  narrative,
  secretObjective,
  onEnter,
}: IsekaiIntroProps) {
  const { t } = useTranslation();
  const words = useMemo(
    () => narrative.split(/(\s+)/).filter(Boolean),
    [narrative],
  );
  const narrativeDuration = words.length * 0.015 + 0.3;

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onEnter();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onEnter]);

  return (
    <div className='intro-overlay'>
      <div
        className='intro-card'
        style={{ animation: 'intro-fade-in 0.3s ease forwards' }}
      >
        <p>
          <NarrativeWords text={narrative} />
        </p>

        <div
          style={{
            opacity: 0,
            animation: `intro-fade-in 0.4s ease forwards`,
            animationDelay: `${narrativeDuration}s`,
            animationFillMode: 'forwards',
          }}
        >
          <h3>{t('game_ui.isekai.secret_objective')}</h3>
          <p>{secretObjective}</p>
        </div>

        <button
          type='button'
          onClick={onEnter}
          autoFocus
          style={{
            opacity: 0,
            animation: `intro-fade-in 0.3s ease forwards`,
            animationDelay: `${narrativeDuration + 0.5}s`,
            animationFillMode: 'forwards',
          }}
        >
          {t('game_ui.isekai.enter')}
        </button>
      </div>
    </div>
  );
}
