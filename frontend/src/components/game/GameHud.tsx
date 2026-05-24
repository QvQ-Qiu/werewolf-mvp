import { Button } from '../ui/Button'
import { RoleCardImage } from './RoleCardImage'
import type { Role } from '../../types/game'

interface GameHudProps {
  onLeave?: () => void
}

export function IdentitySlot({
  seat,
  role,
  roleLabel,
  onShowIdentity,
}: {
  seat: number
  role: Role | null
  roleLabel: string
  onShowIdentity?: () => void
}) {
  if (role && onShowIdentity) {
    return (
      <button
        type="button"
        className="identity-card identity-card--horizontal identity-card--clickable"
        aria-label={`查看身份：${roleLabel}，${seat} 号`}
        onClick={onShowIdentity}
      >
        <RoleCardImage role={role} compact />
        <span className="identity-card__info">
          <span className="identity-card__seat-inline">{seat}号</span>
          <span className="role-pill role-pill--inline">{roleLabel}</span>
        </span>
      </button>
    )
  }

  return (
    <div className="identity-card identity-card--horizontal" aria-label={`${seat} 号，${roleLabel}`}>
      <span className="identity-card__seat-inline">{seat}号</span>
      <span className="role-pill role-pill--inline">{roleLabel}</span>
    </div>
  )
}

export function GameHud({ onLeave }: GameHudProps) {
  return (
    <header className="game-hud game-hud--dense">
      <div className="game-hud__row">
        <div className="game-hud__brand">
          <span className="text-flourish block leading-none">Eclipse Chamber</span>
          <span className="text-eyebrow block leading-tight">月蚀议事厅</span>
        </div>

        {onLeave ? (
          <div className="game-hud__actions">
            <Button variant="secondary" size="sm" onClick={onLeave} className="game-hud__leave">
              退出本局
            </Button>
          </div>
        ) : null}
      </div>
    </header>
  )
}
