import { useEffect, useRef } from 'react'
import { cn } from '../../lib/cn'
import { PRIVATE_CHANNEL_LABEL } from '../../lib/labels'
import type { PrivateMessage } from '../../types/game'

export function PrivateLogPanel({ messages }: { messages: PrivateMessage[] }) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const visible = messages.filter((m) => m.channel !== 'wolf_pack')

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [visible.length, visible[visible.length - 1]?.id])
  if (visible.length === 0) return null

  return (
    <section className="shrink-0 border-t border-subtle bg-[var(--bg-accent-wash)] px-2 py-2 sm:px-3">
      <header className="mb-1.5 flex items-center justify-between gap-2">
        <span className="text-eyebrow text-[10px]">私域 · 仅你可见</span>
        <span className="font-mono text-[10px] text-dim">{visible.length}</span>
      </header>
      <div
        ref={scrollRef}
        className="max-h-[7.5rem] space-y-1.5 overflow-y-auto overscroll-y-contain text-xs"
        aria-live="polite"
      >
        {visible.map((msg) => {
          const channel = PRIVATE_CHANNEL_LABEL[msg.channel] ?? msg.channel
          return (
            <div
              key={msg.id}
              className={cn(
                'border-l-2 pl-2 leading-relaxed',
                msg.channel === 'seer_result' ? 'border-warm text-mist' : 'border-highlight text-muted',
              )}
            >
              <span className="text-[10px] uppercase tracking-wide text-dim">{channel}</span>
              {msg.sender_seat != null ? (
                <span className="ml-1.5 text-dim">{msg.sender_seat}号</span>
              ) : null}
              <p className="mt-0.5 text-mist">{msg.content}</p>
            </div>
          )
        })}
      </div>
    </section>
  )
}
