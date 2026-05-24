import { cn } from '../../../lib/cn'

export function TargetSeatGrid({
  seats,
  selected,
  onSelect,
  disabled,
  labelForSeat,
  columns = 3,
  compact = false,
}: {
  seats: number[]
  selected: number | ''
  onSelect: (seat: number | '') => void
  disabled?: boolean
  labelForSeat?: (seat: number) => string | undefined
  columns?: 2 | 3 | 4 | 5
  compact?: boolean
}) {
  const colClass =
    columns === 2
      ? 'grid-cols-2'
      : columns === 4
        ? 'grid-cols-2 sm:grid-cols-4'
        : columns === 5
          ? 'grid-cols-3 sm:grid-cols-5'
          : 'grid-cols-2 sm:grid-cols-3'

  return (
    <div
      className={cn('target-seat-grid mb-4 grid gap-2', colClass, compact && 'target-seat-grid--compact')}
      role="listbox"
      aria-label="选择目标座位"
    >
      {seats.map((seat) => {
        const isSelected = selected === seat
        const extra = labelForSeat?.(seat)
        return (
          <button
            key={seat}
            type="button"
            role="option"
            aria-selected={isSelected}
            className={cn(
              'game-seat focus-ring flex min-h-[2.75rem] flex-col items-center justify-center px-2 py-2 text-sm transition-colors',
              isSelected && 'game-seat--vote',
              !isSelected && 'hover:border-[var(--border-active)]',
            )}
            onClick={() => onSelect(isSelected ? '' : seat)}
            disabled={disabled}
          >
            <span className="target-seat-grid__num text-display text-base leading-none">{seat}</span>
            <span className="target-seat-grid__suffix mt-0.5 text-[10px] text-muted">号</span>
            {extra && <span className="mt-0.5 max-w-full truncate text-[10px] text-warm">{extra}</span>}
          </button>
        )
      })}
    </div>
  )
}
