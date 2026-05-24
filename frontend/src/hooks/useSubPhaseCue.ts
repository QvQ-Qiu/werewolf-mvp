import { useEffect, useRef } from 'react'
import type { SubPhaseCueView } from '../lib/subPhaseCue'
import { useGameStore } from '../stores/gameStore'

export type { SubPhaseCueView }

export function useSubPhaseCue() {
  const cue = useGameStore((s) => s.subPhaseCue)
  const setSubPhaseCue = useGameStore((s) => s.setSubPhaseCue)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!cue) return
    if (timerRef.current) window.clearTimeout(timerRef.current)
    const duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 600 : 2200
    timerRef.current = window.setTimeout(() => setSubPhaseCue(null), duration)
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current)
    }
  }, [cue, setSubPhaseCue])

  return cue
}
