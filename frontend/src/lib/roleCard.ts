import type { Role } from '../types/game'

/** 静态身份牌资源（frontend/public/role_cards） */
export function roleCardUrl(role: Role): string {
  return `/role_cards/${role}.png`
}
