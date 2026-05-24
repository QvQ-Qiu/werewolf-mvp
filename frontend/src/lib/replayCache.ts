import type { GameReplayResponse } from '../types/replay'

export const REPLAY_CACHE_KEY = (gameId: string) => `werewolf:replay-cache:${gameId}`

export function saveReplayCache(gameId: string, data: GameReplayResponse): void {
  try {
    sessionStorage.setItem(REPLAY_CACHE_KEY(gameId), JSON.stringify(data))
  } catch {
    /* quota */
  }
}

export function loadReplayCache(gameId: string): GameReplayResponse | null {
  const raw = sessionStorage.getItem(REPLAY_CACHE_KEY(gameId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as GameReplayResponse
  } catch {
    return null
  }
}
