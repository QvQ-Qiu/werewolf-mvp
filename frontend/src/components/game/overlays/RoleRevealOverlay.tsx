import { Button } from '../../ui/Button'
import { RoleCardImage } from '../RoleCardImage'
import { ROLE_HINT, ROLE_LABEL } from '../../../lib/labels'
import type { Role } from '../../../types/game'

export function RoleRevealOverlay({
  seat,
  role,
  onConfirm,
}: {
  seat: number
  role: Role
  onConfirm: () => void
}) {
  const roleLabel = ROLE_LABEL[role]
  const hint = ROLE_HINT[role]

  return (
    <div className="cinematic-layer cinematic-layer--modal" role="dialog" aria-modal="true" aria-labelledby="role-reveal-title">
      <div className="cinematic-modal cinematic-modal--role panel-surface">
        <p className="text-flourish mb-0.5">Your Fate</p>
        <p className="text-eyebrow mb-1.5">身份揭示</p>
        <div className="role-card-frame">
          <RoleCardImage role={role} reveal />
        </div>
        <h2 id="role-reveal-title" className="text-display role-modal__title">
          {roleLabel}
        </h2>
        <p className="role-modal__seat text-warm">
          你的席位 · <span className="text-display text-base">{seat}</span> 号
        </p>
        <p className="role-modal__hint font-light text-mist">{hint}</p>
        <Button size="md" className="w-full" onClick={onConfirm}>
          进入议事厅
        </Button>
      </div>
    </div>
  )
}
