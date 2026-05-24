import { CheckCircle2, Info } from 'lucide-react'
import { cn } from '../../lib/cn'
import type { ActionFeedback } from '../../stores/gameStore'

export function ActionFeedbackToast({ feedback }: { feedback: ActionFeedback }) {
  const Icon = feedback.success ? CheckCircle2 : Info
  return (
    <div
      className={cn(
        'pointer-events-none fixed bottom-24 left-1/2 z-[60] flex max-w-[min(24rem,calc(100vw-2rem))] -translate-x-1/2 items-start gap-2 rounded-sm border px-4 py-3',
        feedback.success
          ? 'border-[var(--border-active)] bg-[var(--bg-glass-solid)]'
          : 'border-subtle bg-[var(--bg-glass-solid)]',
      )}
      role="status"
      aria-live="polite"
    >
      <Icon
        className={cn('mt-0.5 h-4 w-4 shrink-0', feedback.success ? 'text-warm' : 'text-muted')}
        aria-hidden
      />
      <p className="text-sm leading-snug text-mist">{feedback.message}</p>
    </div>
  )
}
