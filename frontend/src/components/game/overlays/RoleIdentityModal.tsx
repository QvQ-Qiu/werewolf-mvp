import { Button } from '../../ui/Button'
import { RoleCardImage } from '../RoleCardImage'
import { ROLE_HINT, ROLE_LABEL } from '../../../lib/labels'
import type { Role } from '../../../types/game'

export function RoleIdentityModal({
  seat,
  role,
  onClose,
}: {
  seat: number
  role: Role
  onClose: () => void
}) {
  const roleLabel = ROLE_LABEL[role]
  const hint = ROLE_HINT[role]

  return (
    <div
      className="cinematic-layer cinematic-layer--modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="role-identity-title"
      onClick={onClose}
    >
      <div
        className="cinematic-modal cinematic-modal--role panel-surface"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-flourish mb-0.5">Your Role</p>
        <p className="text-eyebrow mb-1.5">身份 · {seat} 号</p>
        <div className="role-card-frame">
          <RoleCardImage role={role} reveal />
        </div>
        <h2 id="role-identity-title" className="text-display role-modal__title">
          {roleLabel}
        </h2>
        <p className="role-modal__hint font-light text-mist">{hint}</p>
        <Button size="md" className="w-full" onClick={onClose}>
          关闭
        </Button>
      </div>
    </div>
  )
}
