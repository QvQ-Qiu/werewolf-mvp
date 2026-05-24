import type { PublicLogEntry, Role } from './game'

export type ReplayWinner = 'wolf' | 'village'

/** GET /games/{id}/replay 响应（与后端 GameReplayResponse 对齐） */
export interface GameReplayResponse {
  game_id: string
  status: string
  phase: string
  day_number: number
  winner: ReplayWinner | null
  human_seat: number
  players: ReplayPlayerInfo[]
  public_log: PublicLogEntry[]
  llm_traces: LlmTraceDto[]
  private_messages: ReplayPrivateMessage[]
  belief_by_seat?: BeliefStateDto[]
  player_memories?: PlayerMemoryDto[]
}

export interface BeliefStateDto {
  seat: number
  suspects: number[]
  trusted: number[]
  role_claims: Record<string, string>
  open_questions: string[]
}

export interface PlayerMemoryDto {
  seat: number
  strategy_history: Record<string, unknown>[]
  public_claims: Record<string, unknown>[]
  vote_history: Record<string, unknown>[]
}

export interface ReplayPlayerInfo {
  seat: number
  name: string
  role: Role
  is_alive: boolean
  is_human: boolean
  persona_id?: string | null
  personality_name?: string | null
}

export interface LlmTraceDto {
  player_seat: number
  step: string
  strategy_id?: string | null
  phase_ref?: string
  prompt_summary: string
  response_summary: string
  timestamp: string
}

export interface ReplayPrivateMessage {
  id: string
  sender_seat: number | null
  receiver_seat: number
  channel: string
  content: string
  phase_ref: string
  visible_to: number[]
  timestamp: string
}

export interface TimelineEvent {
  id: string
  phase: string
  seat: number | null
  content: string
  time: string
}

export interface ThoughtEntry {
  id: string
  seat: number
  round: string
  roundOrder: number
  kind: 'strategy' | 'thought' | 'action' | 'speech' | 'vote' | 'private'
  label: string
  content: string
}

export interface PlayerDossier {
  seat: number
  name: string
  role: string
  alive: boolean
  personality?: string
  entries: ThoughtEntry[]
}
