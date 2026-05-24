import { cn } from '../../lib/cn'

type Tone = 'neutral' | 'success' | 'warning' | 'error' | 'accent'

const toneClass: Record<Tone, string> = {
  neutral: 'border-[var(--border-subtle)] text-muted',
  success: 'border-[var(--border-medium)] text-warm',
  warning: 'border-[var(--border-medium)] text-soft',
  error: 'border-[var(--border-medium)] text-dim',
  accent: 'border-[var(--border-active)] text-highlight',
}

export function Badge({
  children,
  tone = 'neutral',
  className,
  title,
}: {
  children: React.ReactNode
  tone?: Tone
  className?: string
  title?: string
}) {
  return (
    <span
      title={title}
      className={cn(
        'inline-flex items-center gap-1.5 border bg-[rgba(20,17,14,0.68)] px-2 py-0.5 text-xs font-light',
        toneClass[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
