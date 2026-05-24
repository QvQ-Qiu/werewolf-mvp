import { Eye } from 'lucide-react'
import { cn } from '../../../lib/cn'
import { Button } from '../../ui/Button'

export function SeerCheckResultOverlay({
  targetSeat,
  resultLabel,
  isWolf,
  onConfirm,
}: {
  targetSeat: number
  resultLabel: string
  isWolf: boolean
  onConfirm: () => void
}) {
  return (
    <div className="cinematic-layer cinematic-layer--modal" role="dialog" aria-modal="true">
      <div className="cinematic-modal panel-surface max-w-sm">
        <div className="mb-4 flex items-start gap-2 border-b border-subtle pb-3">
          <Eye className="mt-0.5 h-5 w-5 shrink-0 text-warm" aria-hidden />
          <div>
            <p className="text-flourish mb-0.5">Seer</p>
            <p className="text-eyebrow mb-0.5">预言家 · 仅你可见</p>
            <h2 className="dock-section-title text-base">验人结果</h2>
          </div>
        </div>
        <p className="mb-2 text-sm text-mist">
          查验目标：<span className="font-mono text-warm">{targetSeat} 号</span>
        </p>
        <p className={cn('mb-4 text-display text-lg', isWolf ? 'text-wolf' : 'text-highlight')}>
          身份：{resultLabel}
        </p>
        <Button onClick={onConfirm}>确认</Button>
      </div>
    </div>
  )
}
