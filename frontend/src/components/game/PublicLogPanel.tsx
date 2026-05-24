import { useEffect, useRef } from 'react'
import { cn } from '../../lib/cn'
import { LOG_TYPE_LABEL } from '../../lib/labels'
import type { PublicLogEntry, StreamingSpeech } from '../../types/game'

function bubbleClass(type: string) {
  if (type === 'speech') return 'chat-bubble chat-bubble--speech'
  if (type === 'vote') return 'chat-bubble chat-bubble--vote'
  if (type === 'death') return 'chat-bubble chat-bubble--death'
  return 'chat-bubble chat-bubble--system'
}

function pillClass(type: string) {
  return cn('log-type-pill', type === 'speech' && 'log-type-pill--speech')
}

export function PublicLogPanel({
  entries,
  streamingSpeech = null,
  embedded = false,
}: {
  entries: PublicLogEntry[]
  streamingSpeech?: StreamingSpeech | null
  embedded?: boolean
}) {
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [entries.length, entries[entries.length - 1]?.id, streamingSpeech?.content])

  const scroll = (
    <div
      ref={scrollRef}
      className={cn(
        'game-log-scroll min-h-0 flex-1 overflow-y-auto overscroll-y-contain',
        embedded ? 'px-2.5 py-2' : 'px-4 py-3',
      )}
      aria-live="polite"
      aria-relevant="additions"
    >
      {entries.length === 0 && (
        <div className={cn('text-center', embedded ? 'py-10' : 'py-12')}>
          <p className="text-eyebrow mb-2">公屏</p>
          <p className="text-sm text-muted">等待系统广播与玩家发言…</p>
        </div>
      )}
      <ol className={embedded ? 'space-y-2.5' : 'space-y-3'}>
        {entries.map((entry) => {
          const typeLabel = LOG_TYPE_LABEL[entry.type] ?? entry.type
          return (
            <li key={entry.id} className={cn(embedded && bubbleClass(entry.type))}>
              <div className="mb-1 flex flex-wrap items-center gap-2">
                {entry.seat != null ? (
                  <span className="log-seat-num">{entry.seat}号</span>
                ) : null}
                <span className={pillClass(entry.type)}>{typeLabel}</span>
              </div>
              <p className="break-words text-[0.9375rem] font-normal leading-relaxed text-mist">
                {entry.content}
              </p>
            </li>
          )
        })}
        {streamingSpeech && (
          <li className={cn(embedded && 'chat-bubble chat-bubble--speech', 'opacity-95')}>
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="log-seat-num">{streamingSpeech.seat}号</span>
              <span className={pillClass('speech')}>发言</span>
              <span className="text-[0.65rem] uppercase tracking-wider text-dim">生成中</span>
            </div>
            <p className="break-words text-[0.9375rem] font-normal leading-relaxed text-mist">
              {streamingSpeech.content || (
                <span className="text-dim">正在组织发言…</span>
              )}
              <span className="stream-cursor" aria-hidden>
                ▍
              </span>
            </p>
          </li>
        )}
      </ol>
    </div>
  )

  if (embedded) {
    return <div className="game-log-zone flex h-full min-h-0 min-w-0 flex-col overflow-hidden">{scroll}</div>
  }

  return (
    <section className="panel-surface flex h-full min-h-[280px] flex-col overflow-hidden lg:min-h-[420px]">
      <header className="shrink-0 border-b border-subtle px-4 py-3">
        <h2 className="text-display text-sm">公屏日志</h2>
        <p className="text-caption">系统消息、发言与票型</p>
      </header>
      {scroll}
    </section>
  )
}
