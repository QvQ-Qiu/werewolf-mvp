import { Link, useLocation } from 'react-router-dom'
import { Moon } from 'lucide-react'
import { cn } from '../../lib/cn'

export function AppShell({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()
  const inGame = pathname.startsWith('/game/')

  return (
    <div className={cn('narrative-bg flex min-h-screen flex-col', inGame && 'phase-game h-[100dvh] overflow-hidden')}>
      {!inGame && (
        <header className="sticky top-0 z-40 border-b border-medium bg-[var(--bg-header)]">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
            <Link to="/" className="focus-ring group flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center border border-subtle bg-[var(--bg-accent-wash)] text-warm">
                <Moon className="h-5 w-5" aria-hidden />
              </span>
              <span>
                <span className="text-flourish block text-[10px] leading-none">Eclipse Chamber</span>
                <span className="text-display block text-base leading-tight text-highlight group-hover:text-mist">
                  月蚀议事厅
                </span>
                <span className="text-xs text-muted">十人狼人杀 · 预女猎守</span>
              </span>
            </Link>
            <span className="hidden text-xs text-muted sm:inline">1 人 + 9 AI</span>
          </div>
        </header>
      )}
      <main
        className={cn(
          'relative z-[1] mx-auto w-full flex-1',
          inGame
            ? 'flex h-full max-w-none flex-col overflow-hidden px-1.5 py-1 sm:px-2 sm:py-1.5'
            : 'max-w-7xl px-4 py-6 sm:px-6 sm:py-8',
        )}
      >
        {children}
      </main>
    </div>
  )
}
