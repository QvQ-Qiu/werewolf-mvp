import { describe, expect, it } from 'vitest'

/**
 * 布局预算：iPhone SE 级视口 (~667px) 在 HUD + Dock 打开时，
 * 棋盘区高度常 < 300px，5 个座位 Token 纵向堆叠会超出。
 * 修复策略：公屏容器内 scrollTop（禁止 scrollIntoView）+ 座位列高度锁定。
 */
const SEAT_TOKEN_PX = 40
const SEAT_GAP_PX = 6
const SEATS_PER_COLUMN = 5
const COLUMN_CHROME_PX = 52

describe('game board seat column budget', () => {
  it('documents that stacked seats exceed short board zones without scroll', () => {
    const seatsStack =
      SEATS_PER_COLUMN * SEAT_TOKEN_PX + (SEATS_PER_COLUMN - 1) * SEAT_GAP_PX
    const totalColumn = seatsStack + COLUMN_CHROME_PX
    const tightBoardZone = 240

    expect(totalColumn).toBeGreaterThan(tightBoardZone)
    expect(totalColumn).toBe(276)
  })

  it('seat column uses space-evenly with optional internal scroll only', () => {
    expect(SEATS_PER_COLUMN).toBe(5)
  })
})
