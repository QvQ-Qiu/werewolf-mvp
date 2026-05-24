import { useState } from 'react'
import { Brain, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '../../lib/cn'
import type { MindLogEntry } from '../../lib/formatMindLog'

export function NpcMindPanel({ entries }: { entries: MindLogEntry[] }) {
  const [open, setOpen] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  if (entries.length === 0) return null

  return (
    <div
      className={cn(
        'pointer-events-auto fixed bottom-3 right-3 z-[55] flex w-[min(22rem,calc(100vw-1.5rem))] flex-col border border-subtle bg-[var(--bg-glass-solid)]',
        !open && 'w-auto',
      )}
    >
      <button
        type="button"
        className="flex items-center gap-2 border-b border-subtle px-3 py-2 text-left text-xs"
        onClick={() => setOpen((v) => !v)}
      >
        <Brain className="h-3.5 w-3.5 shrink-0 text-warm" aria-hidden />
        <span className="text-eyebrow text-[10px]">NPC 思考 / 决策</span>
        <span className="ml-auto font-mono text-[10px] text-dim">{entries.length}</span>
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 text-dim" aria-hidden />
        ) : (
          <ChevronUp className="h-3.5 w-3.5 text-dim" aria-hidden />
        )}
      </button>

      {open && (
        <div className="max-h-[40vh] overflow-y-auto overscroll-y-contain px-2 py-2 text-[11px] leading-relaxed">
          <ol className="space-y-2">
            {entries.map((e) => {
              const isExpanded = expandedId === e.id
              return (
                <li key={e.id} className="border-l border-[var(--border-medium)] pl-2">
                  <button
                    type="button"
                    className="w-full text-left text-mist hover:text-highlight"
                    onClick={() => setExpandedId(isExpanded ? null : e.id)}
                  >
                    <span
                      className={cn(
                        'block',
                        e.kind === 'system' && 'text-warm',
                      )}
                    >
                      {e.summary}
                    </span>
                  </button>
                  {isExpanded && e.kind === 'llm' && (
                    <div className="mt-1.5 space-y-1.5 text-dim">
                      {e.phaseRef ? (
                        <p className="text-[10px] text-muted">{e.phaseRef}</p>
                      ) : null}
                      <div>
                        <p className="text-[10px] uppercase tracking-wide text-muted">输入提示词</p>
                        <pre className="code-inset mt-0.5 max-h-32 overflow-auto whitespace-pre-wrap break-words p-1.5 text-[10px] text-mist">
                          {e.promptText}
                        </pre>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-wide text-muted">LLM 输出</p>
                        <pre className="code-inset mt-0.5 max-h-24 overflow-auto whitespace-pre-wrap break-words p-1.5 text-[10px] text-mist">
                          {e.responseText || '（空）'}
                        </pre>
                      </div>
                    </div>
                  )}
                </li>
              )
            })}
          </ol>
        </div>
      )}
    </div>
  )
}
