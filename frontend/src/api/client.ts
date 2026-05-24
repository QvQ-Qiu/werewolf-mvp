import type { CreateGameResponse, GameSession } from '../types/game'
import { saveSession } from '../types/game'
import type {
  LibraryListItem,
  PersonalityLibrary,
  StrategyLibrary,
} from '../types/libraries'
import type { GameReplayResponse } from '../types/replay'

import { consumeSseDeltas } from '../lib/sse'

const API_BASE = import.meta.env.VITE_API_BASE ?? '/api'

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string | { msg?: string }[] }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg
  } catch {
    /* ignore */
  }
  return `HTTP ${res.status}`
}

export interface CreateGameOptions {
  seed?: number
  personalityLibraryId?: string
  strategyLibraryId?: string
}

export async function createGame(
  playerName: string,
  options?: CreateGameOptions,
): Promise<CreateGameResponse> {
  const res = await fetch(`${API_BASE}/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      player_name: playerName,
      seed: options?.seed ?? null,
      personality_library_id: options?.personalityLibraryId ?? 'default',
      strategy_library_id: options?.strategyLibraryId ?? 'default',
    }),
  })
  if (!res.ok) {
    throw new Error(await parseErrorMessage(res))
  }
  const data: CreateGameResponse = await res.json()
  const session: GameSession = {
    game_id: data.game_id,
    player_token: data.player_token,
    human_seat: data.human_seat,
    human_role: data.human_role,
    ws_url: data.ws_url,
  }
  saveSession(session)
  return data
}

export interface LlmHealthStatus {
  configured: boolean
  reachable: boolean
  provider?: string
  model?: string
  error?: string | null
}

export async function checkHealth(): Promise<{
  ok: boolean
  llm?: LlmHealthStatus
}> {
  try {
    const res = await fetch(`${API_BASE}/health`)
    if (!res.ok) return { ok: false }
    const data = (await res.json()) as { llm?: LlmHealthStatus }
    return { ok: true, llm: data.llm }
  } catch {
    return { ok: false }
  }
}

/** 流式 LLM 对话（对接后端 POST /llm/chat/stream） */
export async function streamLlmChat(
  messages: Array<{ role: string; content: string }>,
  onDelta: (delta: string) => void,
  options?: { signal?: AbortSignal; systemPrompt?: string },
): Promise<void> {
  const res = await fetch(`${API_BASE}/llm/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      system_prompt: options?.systemPrompt ?? '',
    }),
    signal: options?.signal,
  })
  await consumeSseDeltas(res, onDelta)
}

// --- 人格库 / 策略库 ---

export async function listPersonalityLibraries(): Promise<LibraryListItem[]> {
  const res = await fetch(`${API_BASE}/libraries/personalities`)
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<LibraryListItem[]>
}

export async function fetchPersonalityLibrary(id: string): Promise<PersonalityLibrary> {
  const res = await fetch(`${API_BASE}/libraries/personalities/${encodeURIComponent(id)}`)
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<PersonalityLibrary>
}

export async function createPersonalityLibrary(body: {
  name: string
  fork_from?: string
}): Promise<PersonalityLibrary> {
  const res = await fetch(`${API_BASE}/libraries/personalities`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<PersonalityLibrary>
}

export async function updatePersonalityLibrary(
  id: string,
  body: { name?: string; personalities?: PersonalityLibrary['personalities'] },
): Promise<PersonalityLibrary> {
  const res = await fetch(`${API_BASE}/libraries/personalities/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<PersonalityLibrary>
}

export async function deletePersonalityLibrary(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/libraries/personalities/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await parseErrorMessage(res))
}

export async function listStrategyLibraries(): Promise<LibraryListItem[]> {
  const res = await fetch(`${API_BASE}/libraries/strategies`)
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<LibraryListItem[]>
}

export async function fetchStrategyLibrary(id: string): Promise<StrategyLibrary> {
  const res = await fetch(`${API_BASE}/libraries/strategies/${encodeURIComponent(id)}`)
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<StrategyLibrary>
}

export async function createStrategyLibrary(body: {
  name: string
  fork_from?: string
}): Promise<StrategyLibrary> {
  const res = await fetch(`${API_BASE}/libraries/strategies`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<StrategyLibrary>
}

export async function updateStrategyLibrary(
  id: string,
  body: { name?: string; strategies_by_role?: StrategyLibrary['strategies_by_role'] },
): Promise<StrategyLibrary> {
  const res = await fetch(`${API_BASE}/libraries/strategies/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<StrategyLibrary>
}

export async function extendStrategyLibrary(
  id: string,
  body: { name?: string; append_by_role: StrategyLibrary['strategies_by_role'] },
): Promise<StrategyLibrary> {
  const res = await fetch(`${API_BASE}/libraries/strategies/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await parseErrorMessage(res))
  return res.json() as Promise<StrategyLibrary>
}

export async function deleteStrategyLibrary(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/libraries/strategies/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error(await parseErrorMessage(res))
}

export async function fetchGameReplay(gameId: string, token?: string): Promise<GameReplayResponse> {
  const q = token ? `?token=${encodeURIComponent(token)}` : ''
  const res = await fetch(`${API_BASE}/games/${encodeURIComponent(gameId)}/replay${q}`)
  if (!res.ok) {
    throw new Error(await parseErrorMessage(res))
  }
  const data = (await res.json()) as GameReplayResponse
  return data
}
