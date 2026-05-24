import { describe, expect, it } from 'vitest'
import { playerOutcome } from './gameOutcome'

describe('playerOutcome', () => {
  it('wolf wins when player is wolf', () => {
    expect(playerOutcome('wolf', 'wolf')).toBe('victory')
  })

  it('village wins when player is villager', () => {
    expect(playerOutcome('villager', 'village')).toBe('victory')
  })

  it('player loses when factions mismatch', () => {
    expect(playerOutcome('wolf', 'village')).toBe('defeat')
    expect(playerOutcome('seer', 'wolf')).toBe('defeat')
  })
})
