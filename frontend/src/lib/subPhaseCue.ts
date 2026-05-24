import { NIGHT_FALL_CUE, NIGHT_WAKE_CUE } from './labels'
import type { Role, SubPhase } from '../types/game'

export type SubPhaseCueView = {
  title: string
  subtitle: string
  isYourTurn: boolean
}

export function buildSubPhaseCue(
  payload: {
    cue_kind: 'night_fall' | 'night_wake' | 'hunter_wake'
    sub_phase: SubPhase
    active_role: Role | null
  },
  yourRole: Role | null,
): SubPhaseCueView | null {
  if (payload.cue_kind === 'night_fall') {
    return { ...NIGHT_FALL_CUE, isYourTurn: false }
  }

  if (payload.cue_kind === 'hunter_wake') {
    const isYou = yourRole === 'hunter'
    return {
      ...NIGHT_WAKE_CUE.hunter,
      subtitle: isYou ? NIGHT_WAKE_CUE.hunter.subtitle : '请保持闭眼',
      isYourTurn: isYou,
    }
  }

  if (payload.cue_kind === 'night_wake' && payload.active_role) {
    const role = payload.active_role
    const isYou = yourRole === role
    const base = NIGHT_WAKE_CUE[role]
    return {
      title: base.title,
      subtitle: isYou ? base.subtitle : '请保持闭眼',
      isYourTurn: isYou,
    }
  }

  return null
}
