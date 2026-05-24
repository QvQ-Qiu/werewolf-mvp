import { useEffect, useRef, useState } from 'react'
import { useGameStore } from '../stores/gameStore'
import type { Phase } from '../types/game'

const ROLE_SEEN_KEY = (gameId: string) => `werewolf:role-seen:${gameId}`

export type PhaseCue = { kind: 'night' | 'day'; dayNumber: number }

export function useGameCinematic(gameId: string | undefined) {
  const phase = useGameStore((s) => s.phase)
  const dayNumber = useGameStore((s) => s.dayNumber)
  const yourRole = useGameStore((s) => s.yourRole)

  const [phaseCue, setPhaseCue] = useState<PhaseCue | null>(null)
  const [roleRevealOpen, setRoleRevealOpen] = useState(false)
  const prevPhaseRef = useRef<Phase | null>(null)
  const phaseInitializedRef = useRef(false)
  const pendingPhaseRef = useRef<PhaseCue | null>(null)

  useEffect(() => {
    if (!phase || phase === 'setup' || phase === 'game_over') {
      prevPhaseRef.current = phase
      return
    }

    if (!phaseInitializedRef.current) {
      phaseInitializedRef.current = true
      const prev = prevPhaseRef.current
      if ((prev === null || prev === 'setup') && dayNumber > 0) {
        let cue: PhaseCue | null = null
        // 入夜由 SUB_PHASE_CUE「天黑请闭眼」承担，不再叠「夜幕降临」
        if (phase === 'day') cue = { kind: 'day', dayNumber }
        if (cue) {
          if (roleRevealOpen) pendingPhaseRef.current = cue
          else setPhaseCue(cue)
        }
      }
      prevPhaseRef.current = phase
      return
    }

    const prev = prevPhaseRef.current
    if (prev !== phase) {
      let cue: PhaseCue | null = null
      if (phase === 'day' && dayNumber > 0) {
        cue = { kind: 'day', dayNumber }
      }
      if (cue) {
        if (roleRevealOpen) {
          pendingPhaseRef.current = cue
        } else {
          setPhaseCue(cue)
        }
      }
    }
    prevPhaseRef.current = phase
  }, [phase, dayNumber, roleRevealOpen])

  useEffect(() => {
    if (!phaseCue) return
    const duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 500 : 2400
    const t = window.setTimeout(() => setPhaseCue(null), duration)
    return () => window.clearTimeout(t)
  }, [phaseCue])

  useEffect(() => {
    if (!yourRole || !gameId) return
    if (sessionStorage.getItem(ROLE_SEEN_KEY(gameId))) return
    setRoleRevealOpen(true)
  }, [yourRole, gameId])

  function dismissRoleReveal() {
    if (gameId) sessionStorage.setItem(ROLE_SEEN_KEY(gameId), '1')
    setRoleRevealOpen(false)
    if (pendingPhaseRef.current) {
      setPhaseCue(pendingPhaseRef.current)
      pendingPhaseRef.current = null
    }
  }

  const yourSeat = useGameStore((s) => s.yourSeat)

  return {
    phaseCue,
    roleRevealOpen,
    dismissRoleReveal,
    yourRole,
    yourSeat,
  }
}
