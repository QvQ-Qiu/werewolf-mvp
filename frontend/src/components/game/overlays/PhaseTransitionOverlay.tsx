import { cn } from '../../../lib/cn'
import type { PhaseCue } from '../../../hooks/useGameCinematic'

export function PhaseTransitionOverlay({ cue }: { cue: PhaseCue }) {
  const isNight = cue.kind === 'night'

  return (
    <div
      className={cn('cinematic-layer cinematic-layer--phase', isNight ? 'cinematic-layer--night' : 'cinematic-layer--day')}
      role="status"
      aria-live="polite"
      aria-label={isNight ? `第 ${cue.dayNumber} 夜` : `第 ${cue.dayNumber} 日`}
    >
      <div className="cinematic-phase-card">
        <p className="text-flourish text-flourish--lg mb-2">{isNight ? 'Nightfall' : 'Daybreak'}</p>
        <p className="text-eyebrow mb-2">{isNight ? '夜幕降临' : '天亮了'}</p>
        <p className="cinematic-phase-title">
          {isNight ? `第 ${cue.dayNumber} 夜` : `第 ${cue.dayNumber} 日`}
        </p>
        <p className="mt-3 text-sm font-light text-muted">
          {isNight ? '议事厅灯火将熄…' : '阳光重回议事厅…'}
        </p>
      </div>
    </div>
  )
}
