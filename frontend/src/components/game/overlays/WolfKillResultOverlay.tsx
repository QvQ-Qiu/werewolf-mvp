import { MoonStar } from 'lucide-react'
import { Button } from '../../ui/Button'

export function WolfKillResultOverlay({
  killTarget,
  isTie,
  tiedTargets,
  onDismiss,
}: {
  killTarget: number
  isTie: boolean
  tiedTargets: number[]
  onDismiss: () => void
}) {
  return (
    <div className="cinematic-layer cinematic-layer--modal" role="dialog" aria-modal="true">
      <div className="cinematic-modal panel-surface max-w-sm">
        <div className="mb-4 flex items-start gap-2 border-b border-subtle pb-3">
          <MoonStar className="mt-0.5 h-5 w-5 shrink-0 text-warm" aria-hidden />
          <div>
            <p className="text-flourish mb-0.5">Wolf Pack</p>
            <p className="text-eyebrow mb-0.5">狼队 · 仅你可见</p>
            <h2 className="dock-section-title text-base">狼刀结果</h2>
          </div>
        </div>
        <p className="mb-2 text-sm text-mist">
          最终刀口：<span className="font-mono text-warm">{killTarget} 号</span>
        </p>
        {isTie && tiedTargets.length > 0 && (
          <p className="mb-3 text-xs text-muted">
            狼队平票（{tiedTargets.join('、')} 号），系统随机选定 {killTarget} 号
          </p>
        )}
        <Button onClick={onDismiss}>知道了</Button>
      </div>
    </div>
  )
}
