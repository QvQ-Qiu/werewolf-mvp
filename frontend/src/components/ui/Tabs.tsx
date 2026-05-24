import { cn } from '../../lib/cn'

export interface TabItem {
  id: string
  label: string
}

interface TabsProps {
  items: TabItem[]
  activeId: string
  onChange: (id: string) => void
  className?: string
}

export function Tabs({ items, activeId, onChange, className }: TabsProps) {
  return (
    <div role="tablist" className={cn('flex border border-[var(--border-subtle)]', className)}>
      {items.map((item) => {
        const active = item.id === activeId
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.id)}
            className={cn(
              'focus-ring flex-1 border-r border-[var(--border-subtle)] px-4 py-2 text-sm font-light last:border-r-0 transition-colors',
              active
                ? 'bg-[var(--bg-accent-wash-strong)] text-highlight'
                : 'bg-transparent text-muted hover:text-mist',
            )}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
