import { Vote } from 'lucide-react'
import { Button } from '../../ui/Button'
import type { PlayerPublicInfo } from '../../../types/game'
import { TargetSeatGrid } from './TargetSeatGrid'

export function VoteActionModal({
  candidates,
  players,
  target,
  onTarget,
  onSubmit,
  onAbstain,
  disabled,
  pending = false,
}: {
  candidates: number[]
  players: PlayerPublicInfo[]
  target: number | ''
  onTarget: (v: number | '') => void
  onSubmit: () => void
  onAbstain: () => void
  disabled?: boolean
  pending?: boolean
}) {
  function playerName(seat: number): string {
    return players.find((p) => p.seat === seat)?.name ?? `${seat} 号`
  }

  return (
    <div
      className="cinematic-layer cinematic-layer--modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="vote-modal-title"
    >
      <div className="cinematic-modal panel-surface">
        <div className="mb-4 flex items-start gap-2 border-b border-subtle pb-3">
          <Vote className="mt-0.5 h-5 w-5 shrink-0 text-warm" aria-hidden />
          <div className="min-w-0">
            <p className="text-flourish mb-0.5">Day Vote</p>
            <p className="text-eyebrow mb-0.5">白天 · 放逐投票</p>
            <h2 id="vote-modal-title" className="dock-section-title text-base">
              投票放逐
            </h2>
            <p className="mt-1 text-xs text-muted">选择一名存活玩家放逐，或弃票</p>
          </div>
        </div>

        <TargetSeatGrid
          seats={candidates}
          selected={target}
          onSelect={onTarget}
          disabled={disabled || pending}
          labelForSeat={(seat) => playerName(seat)}
        />

        {pending && (
          <p className="mb-3 text-center text-xs text-warm" role="status">
            正在提交投票…
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button onClick={onSubmit} disabled={disabled || pending || target === ''}>
            确认投票
          </Button>
          <Button variant="ghost" onClick={onAbstain} disabled={disabled || pending}>
            弃票
          </Button>
        </div>
      </div>
    </div>
  )
}
