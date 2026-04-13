import { Fragment, memo, useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';

import { useGameStore } from '../../store/gameStore';

function sanitizeEntryContent(content: string): string {
  return content
    .replace(/\s*<game_state>[\s\S]*?<\/game_state>\s*/gi, '')
    .replace(/\s*```game_state[\s\S]*?```\s*/gi, '')
    .replace(/\s*<game_state>[\s\S]*$/gi, '')
    .replace(/\s*```game_state[\s\S]*$/gi, '')
    .replace(/\s*<\/game_state>\s*/gi, '')
    .trim();
}

function formatUserAction(content: string): string {
  const cleaned = sanitizeEntryContent(content);
  const lines = cleaned
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => !/^\[Turn\s+\d+\]$/i.test(line));

  if (lines.length === 0) {
    return cleaned;
  }

  return lines
    .map((line) => line.replace(/^\*\*(.+?)\*\*:\s*/, '$1: '))
    .join('\n');
}

/**
 * Divide texto em palavras e anima cada nova palavra com CSS fade-in.
 * Uses offset as key: existing words keep their DOM node without re-animating;
 * only new words mount with the .streaming-word animation.
 * Substituiu motion.span (Framer Motion) para reduzir overhead em streaming.
 */
const StreamingWords = memo(function StreamingWords({
  content,
}: Readonly<{ content: string }>) {
  const words = useMemo(
    () => content.split(/(\s+)/).filter(Boolean),
    [content],
  );
  let offset = 0;
  return (
    <>
      {words.map((word) => {
        const key = offset;
        offset += word.length;
        return (
          <span key={key} className='streaming-word'>
            {word}
          </span>
        );
      })}
    </>
  );
});

export const NarrativePanel = memo(function NarrativePanel() {
  const { t } = useTranslation();
  const history = useGameStore((state) => state.gameState.history);
  const isStreaming = useGameStore((state) => state.gameState.is_streaming);
  const gmThinking = useGameStore((state) => state.gmThinking);
  const serverError = useGameStore((state) => state.serverError);
  const setServerError = useGameStore((state) => state.setServerError);
  const containerRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    isAtBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight < 60;
  };

  // Scroll to bottom only when user was already at the bottom
  useEffect(() => {
    if (!containerRef.current || !isAtBottomRef.current) return;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
  }, [history, isStreaming]);

  const renderedHistory = useMemo(
    () => history.map((entry) => ({
      ...entry,
      content:
        entry.role === 'user'
          ? formatUserAction(entry.content)
          : sanitizeEntryContent(entry.content),
    })),
    [history],
  );

  return (
    <section
      className='panel narrative'
      ref={containerRef}
      onScroll={handleScroll}
      role='region'
      aria-label={t('narrative.aria_label')}
      aria-live='polite'
      aria-atomic='false'
    >
      {serverError && (
        <div className='server-error-banner' role='alert'>
          <span>⚠ {serverError}</span>
          <button
            type='button'
            onClick={() => setServerError(null)}
            aria-label={t('narrative.close_warning')}
          >
            ×
          </button>
        </div>
      )}

      {renderedHistory.map((entry, index) => {
        const isLastAssistant =
          isStreaming &&
          entry.role === 'assistant' &&
          index === renderedHistory.length - 1;
        const previousTurn = index > 0 ? renderedHistory[index - 1].turn_number : null;
        const showTurnDivider = index === 0 || previousTurn !== entry.turn_number;

        return (
          <Fragment key={`${entry.turn_number}-${entry.role}-${index}`}>
            {showTurnDivider && (
              <div className='turn-divider'>
                <span>Turn {entry.turn_number}</span>
              </div>
            )}
            <article
              className={`entry ${entry.role}`}
            >
              <div className='entry-header'>
                <span className='entry-label'>
                  {entry.role === 'user' ? 'Action' : 'Narration'}
                </span>
              </div>
              {isLastAssistant ? (
                <p>
                  <StreamingWords content={entry.content} />
                </p>
              ) : entry.role === 'user' ? (
                <p className='entry-action'>{entry.content}</p>
              ) : (
                <ReactMarkdown rehypePlugins={[rehypeSanitize]}>
                  {entry.content}
                </ReactMarkdown>
              )}
            </article>
          </Fragment>
        );
      })}

      {history.length === 0 && (
        <p className='empty'>
          {gmThinking ?? t('narrative.narrative_waiting')}
        </p>
      )}
    </section>
  );
});
