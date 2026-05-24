import { cn } from '../../../lib/cn'
import type { SubPhaseCueView } from '../../../lib/subPhaseCue'

export function SubPhaseCueOverlay({ cue }: { cue: SubPhaseCueView }) {
  return (
    <div
      className={cn(
        'cinematic-layer cinematic-layer--phase',
        cue.isYourTurn ? 'cinematic-layer--night' : 'cinematic-layer--night',
      )}
      role="status"
      aria-live="polite"
    >
      <div className="cinematic-phase-card">
        <p className="text-flourish text-flourish--lg mb-2">
          {cue.isYourTurn ? 'Your Turn' : 'Night'}
        </p>
        <p className="text-eyebrow mb-2">
          {cue.title === '天黑请闭眼'
            ? '夜晚开始'
            : cue.isYourTurn
              ? '轮到你行动'
              : '请保持闭眼'}
        </p>
        <p className="cinematic-phase-title">{cue.title}</p>
        <p className="mt-3 text-sm font-light text-muted">{cue.subtitle}</p>
      </div>
    </div>
  )
}
