import { useEffect, useState } from 'react'
import { cn } from '../../lib/cn'

export function Countdown({ deadlineTs }: { deadlineTs: number }) {
  const [left, setLeft] = useState(() => Math.max(0, Math.ceil(deadlineTs - Date.now() / 1000)))

  useEffect(() => {
    const timer = setInterval(() => {
      setLeft(Math.max(0, Math.ceil(deadlineTs - Date.now() / 1000)))
    }, 500)
    return () => clearInterval(timer)
  }, [deadlineTs])

  const urgent = left > 0 && left <= 10

  return (
    <span
      className={cn(
        'font-mono font-light',
        urgent ? 'text-alert animate-pulse' : 'text-highlight',
      )}
      aria-live="polite"
    >
      {left}s
    </span>
  )
}
