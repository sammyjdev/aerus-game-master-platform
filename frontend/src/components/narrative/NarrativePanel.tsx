import { memo, useEffect, useMemo, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';

import { useGameStore } from '../../store/gameStore';

/**
 * Divide texto em palavras e anima cada nova palavra com CSS fade-in.
 * Uses offset as key: existing words keep their DOM node without re-animating;
 * only new words mount with the .streaming-word animation.
 * Substituiu motion.span (Framer Motion) para reduzir overhead em streaming.
 */
const StreamingWords = memo(function StreamingWords({
  content,
}: Readonly<{ content: string }>) {
  const words = useMemo(() => content.split(/(\s+)/).filter(Boolean), [content])
  let offset = 0
  return (
    <>
      {words.map((word) => {
        const key = offset
        offset += word.length
        return (
          <span key={key} className='streaming-word'>
            {word}
          </span>
        )
      })}
    </>
  )
})

export const NarrativePanel = memo(function NarrativePanel() {
  const history = useGameStore((state) => state.gameState.history)
  const isStreaming = useGameStore((state) => state.gameState.is_streaming)
  const gmThinking = useGameStore((state) => state.gmThinking)
  const serverError = useGameStore((state) => state.serverError)
  const setServerError = useGameStore((state) => state.setServerError)
  const containerRef = useRef<HTMLDivElement>(null)
  const isAtBottomRef = useRef(true)

  const handleScroll = () => {
    const el = containerRef.current
    if (!el) return
    isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60
  }

  // Scroll to bottom only when user was already at the bottom
  useEffect(() => {
    if (!containerRef.current || !isAtBottomRef.current) return
    containerRef.current.scrollTop = containerRef.current.scrollHeight
  }, [history, isStreaming])

  return (
    <section
      className='panel narrative'
      ref={containerRef}
      onScroll={handleScroll}
      role='region'
      aria-label='Narrativa do jogo'
      aria-live='polite'
      aria-atomic='false'
    >
      {serverError && (
        <div className='server-error-banner' role='alert'>
          <span>⚠ {serverError}</span>
          <button
            type='button'
            onClick={() => setServerError(null)}
            aria-label='Fechar aviso'
          >
            ×
          </button>
        </div>
      )}

      {history.map((entry, index) => {
        const isLastAssistant =
          isStreaming && entry.role === 'assistant' && index === history.length - 1

        return (
          <article
            key={`${entry.turn_number}-${index}`}
            className={`entry ${entry.role}`}
          >
            {isLastAssistant ? (
              <p>
                <StreamingWords content={entry.content} />
              </p>
            ) : (
              <ReactMarkdown rehypePlugins={[rehypeSanitize]}>
                {entry.content}
              </ReactMarkdown>
            )}
          </article>
        )
      })}

      {history.length === 0 && (
        <p className='empty'>
          {gmThinking ?? 'The narrative begins when all players submit an action.'}
        </p>
      )}
    </section>
  )
})
