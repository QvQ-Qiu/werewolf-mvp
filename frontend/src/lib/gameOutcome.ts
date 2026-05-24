import type { Role } from '../types/game'

export type PlayerOutcome = 'victory' | 'defeat'

/** 根据玩家身份与阵营胜负判断个人胜败 */
export function playerOutcome(yourRole: Role | null, winner: 'wolf' | 'village'): PlayerOutcome {
  if (!yourRole) {
    return winner === 'village' ? 'victory' : 'defeat'
  }
  const isWolf = yourRole === 'wolf'
  const wolfWon = winner === 'wolf'
  return isWolf === wolfWon ? 'victory' : 'defeat'
}

export function winnerFactionLabel(winner: 'wolf' | 'village'): string {
  return winner === 'wolf' ? '狼人阵营' : '好人阵营'
}
