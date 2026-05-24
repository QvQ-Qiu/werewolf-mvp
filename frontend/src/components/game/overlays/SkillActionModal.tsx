import { MoonStar } from 'lucide-react'
import { Button } from '../../ui/Button'
import { NIGHT_ACTION_TITLE } from '../../../lib/labels'
import type { NightActionRequest } from '../../../types/game'
import { TargetSeatGrid } from './TargetSeatGrid'

function nightActionLabel(type: string): string {
  const map: Record<string, string> = {
    wolf_nominate: '提名刀口（由狼队表决）',
    wolf_kill: '提名刀口（由狼队表决）',
    seer_check: '选择查验目标',
    witch_action: '选择用药方式',
    guard_protect: '选择守护目标',
    hunter_shoot: '选择开枪目标',
  }
  return map[type] ?? '选择目标'
}

function WolfNominationRow({
  wolfSeat,
  victim,
  isYou,
}: {
  wolfSeat: number
  victim: number | undefined
  isYou: boolean
}) {
  return (
    <div className="wolf-nomination-row">
      <span
        className={`game-seat wolf-nomination-row__seat shrink-0 items-center justify-center ${
          isYou ? 'game-seat--you' : ''
        }`}
      >
        {wolfSeat}
      </span>
      <span className="wolf-nomination-row__who min-w-0 truncate text-mist">
        {isYou ? '你' : `${wolfSeat} 号`}
        <span className="text-muted"> · 狼</span>
      </span>
      <span className="wolf-nomination-row__kill shrink-0 text-muted">
        刀口：
        {victim != null ? (
          <span className="font-mono text-warm">{victim} 号</span>
        ) : (
          <span className="text-dim">未提名</span>
        )}
      </span>
    </div>
  )
}

function WolfNominationBoard({
  wolfSeats,
  nominations,
  yourSeat,
}: {
  wolfSeats: number[]
  nominations: Record<number, number>
  yourSeat: number
}) {
  const teammates = wolfSeats.filter((s) => s !== yourSeat)
  return (
    <div className="wolf-nomination-board">
      <p className="wolf-nomination-board__title">狼队提名（实时）</p>
      <div className="wolf-nomination-list">
        <div className="wolf-nomination-group">
          <p className="wolf-nomination-group__label">自己</p>
          <WolfNominationRow
            wolfSeat={yourSeat}
            victim={nominations[yourSeat]}
            isYou
          />
        </div>
        {teammates.length > 0 && (
          <div className="wolf-nomination-group">
            <p className="wolf-nomination-group__label">队友刀口</p>
            {teammates.map((wolfSeat) => (
              <WolfNominationRow
                key={wolfSeat}
                wolfSeat={wolfSeat}
                victim={nominations[wolfSeat]}
                isYou={false}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function SkillActionModal({
  request,
  target,
  onTarget,
  onAction,
  disabled,
  pending = false,
  wolfNominations = {},
}: {
  request: NightActionRequest
  target: number | ''
  onTarget: (v: number | '') => void
  onAction: (actionType: string, extra?: Record<string, unknown>) => void
  disabled?: boolean
  pending?: boolean
  wolfNominations?: Record<number, number>
}) {
  const title = NIGHT_ACTION_TITLE[request.action_type] ?? '夜晚行动'
  const nominations = { ...request.wolf_nominations, ...wolfNominations }
  const potionLocked =
    request.potion_used_tonight || request.heal_used || request.poison_used
  const isWolfNight = request.action_type === 'wolf_nominate'
  const wolfSeats = isWolfNight
    ? [request.actor_seat, ...(request.wolf_teammates ?? [])].sort((a, b) => a - b)
    : []
  return (
    <div
      className="cinematic-layer cinematic-layer--modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="skill-modal-title"
    >
      <div className="cinematic-modal cinematic-modal--skill panel-surface">
        <div className="skill-modal__header flex items-start gap-2 border-b border-subtle">
          <MoonStar className="mt-0.5 h-5 w-5 shrink-0 text-warm" aria-hidden />
          <div className="min-w-0">
            <p className="text-flourish mb-0.5">Private Act</p>
            <p className="text-eyebrow mb-0.5">私域 · 仅你可见</p>
            <h2 id="skill-modal-title" className="dock-section-title text-base">
              {title}
            </h2>
            <p className="mt-1 text-xs text-muted">{nightActionLabel(request.action_type)}</p>
          </div>
        </div>

        {request.action_type === 'witch_action' && request.wolf_kill_victim != null && (
          <p className="mb-3 text-xs text-muted">
            昨夜刀口：<span className="font-mono text-mist">{request.wolf_kill_victim} 号</span>
          </p>
        )}

        {request.action_type === 'witch_action' && (
          <p className="mb-3 text-xs text-muted">每夜最多使用一瓶药水（解药或毒药）</p>
        )}

        {isWolfNight && wolfSeats.length > 0 && (
          <WolfNominationBoard
            wolfSeats={wolfSeats}
            nominations={nominations}
            yourSeat={request.actor_seat}
          />
        )}

        {request.action_type !== 'witch_action' && (
          <TargetSeatGrid
            seats={request.alive_seats}
            selected={target}
            onSelect={onTarget}
            disabled={disabled || pending}
            compact={isWolfNight}
          />
        )}

        {request.action_type === 'witch_action' &&
          request.poison_available !== false &&
          !potionLocked && (
            <>
              <p className="mb-2 text-xs text-muted">毒药目标（可选）</p>
              <TargetSeatGrid
                seats={request.alive_seats}
                selected={target}
                onSelect={onTarget}
                disabled={disabled || pending}
              />
            </>
          )}

        {pending && (
          <p className="mb-3 text-center text-xs text-warm" role="status">
            正在提交行动…
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          {request.action_type === 'witch_action' ? (
            <>
              <Button
                onClick={() =>
                  onAction('witch_action', {
                    use_heal: true,
                    target_seat: request.wolf_kill_victim ?? null,
                  })
                }
                disabled={
                  disabled ||
                  request.heal_available === false ||
                  request.heal_used ||
                  potionLocked ||
                  request.wolf_kill_victim == null
                }
              >
                使用解药
              </Button>
              <Button
                variant="secondary"
                onClick={() => onAction('witch_action', { use_poison: true })}
                disabled={
                  disabled ||
                  request.poison_available === false ||
                  request.poison_used ||
                  potionLocked ||
                  target === ''
                }
              >
                使用毒药
              </Button>
              <Button variant="ghost" onClick={() => onAction('pass')} disabled={disabled}>
                跳过
              </Button>
            </>
          ) : request.action_type === 'hunter_shoot' ? (
            <>
              <Button onClick={() => onAction('hunter_shoot')} disabled={disabled || target === ''}>
                开枪
              </Button>
              <Button variant="ghost" onClick={() => onAction('pass')} disabled={disabled}>
                不开枪
              </Button>
            </>
          ) : (
            <>
              <Button onClick={() => onAction(request.action_type)} disabled={disabled || target === ''}>
                确认
              </Button>
              <Button variant="ghost" onClick={() => onAction('pass')} disabled={disabled}>
                跳过
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
