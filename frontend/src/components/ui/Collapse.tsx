import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { cn } from '../../lib/cn'

export function Collapse({
  title,
  children,
  defaultOpen = false,
}: {
  title: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="panel-surface overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="focus-ring flex w-full items-center justify-between gap-2 px-4 py-3 text-left text-sm font-light text-mist"
        aria-expanded={open}
      >
        {title}
        <ChevronDown
          className={cn('h-4 w-4 text-muted transition-transform duration-200', open && 'rotate-180')}
        />
      </button>
      {open && <div className="border-t border-subtle px-4 py-3 text-sm font-light text-muted">{children}</div>}
    </div>
  )
}
