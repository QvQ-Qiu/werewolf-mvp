import { roleCardUrl } from '../../lib/roleCard'
import { ROLE_LABEL } from '../../lib/labels'
import type { Role } from '../../types/game'

export function RoleCardImage({
  role,
  className = '',
  compact = false,
  reveal = false,
}: {
  role: Role
  className?: string
  compact?: boolean
  reveal?: boolean
}) {
  const label = ROLE_LABEL[role]
  const sizeClass = compact
    ? 'role-card-img role-card-img--compact'
    : reveal
      ? 'role-card-img role-card-img--reveal'
      : 'role-card-img'
  return (
    <img
      src={roleCardUrl(role)}
      alt={`${label}身份牌`}
      className={`${sizeClass} ${className}`.trim()}
      loading="lazy"
      draggable={false}
    />
  )
}
