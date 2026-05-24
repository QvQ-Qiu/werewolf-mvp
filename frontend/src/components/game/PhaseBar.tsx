import { cn } from '../../lib/cn'
import { PHASE_LABEL, SUB_PHASE_LABEL } from '../../lib/labels'
import type { Phase, SubPhase } from '../../types/game'

export function PhaseBar({
  phase,
  subPhase,
  dayNumber,
  compact = false,
  prominent = false,
  dense = false,
}: {
  phase: Phase | null
  subPhase: SubPhase | null
  dayNumber: number
  compact?: boolean
  prominent?: boolean
  dense?: boolean
}) {
  const isNight = phase === 'night'
  const dayLabel = dayNumber > 0 ? (isNight ? `第${dayNumber}夜` : `第${dayNumber}日`) : null
  const phaseText = phase ? (PHASE_LABEL[phase] ?? phase) : '等待'
  const subText = subPhase ? (SUB_PHASE_LABEL[subPhase] ?? subPhase) : null

  if (dense) {
    return (
      <div
        className={cn(
          'board-phase',
          isNight && 'board-phase--night',
          phase === 'day' && 'board-phase--day',
        )}
        role="status"
        aria-live="polite"
      >
        <span className="board-phase__hero">{phaseText}</span>
        {dayLabel && (
          <>
            <span className="board-phase__sep" aria-hidden="true">
              ·
            </span>
            <span className="board-phase__day">{dayLabel}</span>
          </>
        )}
        {subText && (
          <>
            <span className="board-phase__sep" aria-hidden="true">
              |
            </span>
            <span className="board-phase__sub">{subText}</span>
          </>
        )}
      </div>
    )
  }

  if (prominent && compact) {
    return (
      <div
        className={cn(
          'space-y-1',
          isNight && 'rounded-sm bg-[var(--bg-night)] px-2 py-1.5',
          phase === 'day' && 'rounded-sm bg-[var(--bg-day)] px-2 py-1.5',
        )}
        role="status"
        aria-live="polite"
      >
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span className="phase-hero">{phaseText}</span>
          {dayLabel && <span className="text-sm font-normal text-mist">{dayLabel}</span>}
        </div>
        {subText && (
          <p className="line-clamp-2 text-sm font-normal leading-snug text-warm">{subText}</p>
        )}
      </div>
    )
  }

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-2',
        !compact && 'panel-surface px-3 py-2',
        !compact && (isNight ? 'bg-[var(--bg-night)]' : phase === 'day' ? 'bg-[var(--bg-day)]' : ''),
      )}
      role="status"
    >
      <span className={cn('tag-flat px-2 py-0.5', phase && 'tag-flat--active')}>{phaseText}</span>
      {subText && <span className="tag-flat px-2 py-0.5 text-warm">{subText}</span>}
      {dayLabel && <span className="text-xs text-muted">{dayLabel}</span>}
    </div>
  )
}
