/** 角色枚举 */
export type Role = 'wolf' | 'seer' | 'witch' | 'hunter' | 'guard' | 'villager'

/** 主阶段 */
export type Phase = 'setup' | 'night' | 'day' | 'game_over'

/** 子阶段 */
export type SubPhase =
  | 'night_wolf'
  | 'night_seer'
  | 'night_witch'
  | 'night_guard'
  | 'night_resolve'
  | 'day_announce'
  | 'day_speech'
  | 'day_vote'
  | 'day_resolve'
  | 'hunter_shoot'

/** 公屏日志条目 */
export interface PublicLogEntry {
  id: string
  type: 'system' | 'speech' | 'vote' | 'death' | 'skill_reveal'
  seat: number | null
  content: string
  timestamp: string
}

/** 公开玩家信息 */
export interface PlayerPublicInfo {
  seat: number
  name: string
  is_alive: boolean
  is_human: boolean
}

/** 发言回合 */
export interface SpeechTurn {
  seat: number
  deadline_ts: number
  is_you: boolean
}

/** AI 发言流式输出（公屏打字机） */
export interface StreamingSpeech {
  seat: number
  content: string
}

/** 夜晚行动请求（与后端 NIGHT_ACTION_REQUEST payload 对齐） */
export interface NightActionRequest {
  action_type: string
  actor_seat: number
  alive_seats: number[]
  wolf_kill_victim?: number | null
  heal_available?: boolean
  heal_used?: boolean
  poison_available?: boolean
  poison_used?: boolean
  potion_used_tonight?: boolean
  wolf_nominations?: Record<number, number>
  wolf_teammates?: number[]
}

/** 私域消息（预言家验人等） */
export interface PrivateMessage {
  id: string
  channel: string
  sender_seat: number | null
  receiver_seat: number
  content: string
  phase_ref: string
  timestamp: string
}

/** WebSocket 事件（服务端 → 客户端） */
export type WsServerEvent =
  | { type: 'CONNECTED'; payload: { game_id: string; message: string } }
  | { type: 'PONG'; payload: Record<string, never> }
  | {
      type: 'GAME_STARTED'
      payload: {
        your_role: Role
        your_seat: number
        players: PlayerPublicInfo[]
        game_deadline_ts?: number
      }
    }
  | { type: 'GAME_TIMEOUT'; payload: { message: string } }
  | { type: 'PHASE_CHANGED'; payload: { phase: Phase; day_number: number; sub_phase?: SubPhase } }
  | {
      type: 'SUB_PHASE_CUE'
      payload: {
        cue_kind: 'night_fall' | 'night_wake' | 'hunter_wake'
        sub_phase: SubPhase
        day_number: number
        active_role: Role | null
      }
    }
  | {
      type: 'ACTION_ACK'
      payload: {
        kind: 'night' | 'vote' | 'speech'
        message: string
        success: boolean
        seat: number
      }
    }
  | { type: 'PUBLIC_LOG'; payload: { entry: PublicLogEntry } }
  | { type: 'SPEECH_STREAM_START'; payload: { seat: number } }
  | { type: 'SPEECH_STREAM_DELTA'; payload: { seat: number; delta: string } }
  | { type: 'SPEECH_STREAM_END'; payload: { seat: number } }
  | { type: 'SPEAK_TURN_START'; payload: SpeechTurn }
  | { type: 'SPEAK_TURN_END'; payload: { seat: number } }
  | { type: 'VOTE_STARTED'; payload: { candidates: number[] } }
  | { type: 'VOTE_RESULT'; payload: { tally: Record<number, number>; eliminated_seat?: number; is_tie: boolean } }
  | {
      type: 'WOLF_NOMINATION_UPDATE'
      payload: { nominations: Record<number, number>; teammates: number[] }
    }
  | {
      type: 'WOLF_KILL_RESULT'
      payload: {
        kill_target: number
        nominations: Record<number, number>
        is_tie: boolean
        tied_targets: number[]
      }
    }
  | {
      type: 'SEER_CHECK_RESULT'
      payload: {
        target_seat: number
        is_wolf: boolean
        result_label: string
      }
    }
  | { type: 'NIGHT_ACTION_REQUEST'; payload: NightActionRequest }
  | { type: 'STATE_SNAPSHOT'; payload: StateSnapshot }
  | { type: 'GAME_END'; payload: { winner: 'wolf' | 'village'; replay_url: string } }
  | { type: 'SPECTATOR_MODE'; payload: { message: string; can_view_private?: boolean } }
  | { type: 'PRIVATE_MESSAGE'; payload: PrivateMessage }
  | {
      type: 'LLM_TRACE'
      payload: {
        player_seat: number
        role: Role | string
        step: string
        phase_ref?: string
        messages: { role: string; content: string }[]
        response: string
        strategy_id?: string | null
        timestamp: string
      }
    }
  | { type: 'ERROR'; payload: { code: string; message: string } }

/** 服务端 filtered_view（STATE_SNAPSHOT 内） */
export interface FilteredPlayerView {
  your_seat?: number
  your_role?: Role | null
  your_seer_checks?: { night: number; target: number; is_wolf: boolean }[]
  witch_heal_available?: boolean
  witch_poison_available?: boolean
  wolf_teammates?: number[]
  private_messages?: { channel: string; sender: number | null; content: string; phase_ref: string }[]
  spectator_mode?: boolean
  note?: string
}

/** 状态快照 */
export interface StateSnapshot {
  phase: Phase
  sub_phase: SubPhase | null
  day_number: number
  players: PlayerPublicInfo[]
  public_log: PublicLogEntry[]
  speech_turn: { seat: number; is_you: boolean } | null
  vote_active: boolean
  winner: 'wolf' | 'village' | null
  spectator_mode?: boolean
  filtered_view?: FilteredPlayerView
}

/** 创建对局响应 */
export interface CreateGameResponse {
  game_id: string
  ws_url: string
  player_token: string
  human_seat: number
  human_role: Role
}

/** 本地会话存储 */
export interface GameSession {
  game_id: string
  player_token: string
  human_seat: number
  human_role: Role
  ws_url?: string
}

export const SESSION_KEY = (gameId: string) => `werewolf:session:${gameId}`

export function normalizeSeatMap(raw: Record<string, number> | Record<number, number>): Record<number, number> {
  return Object.fromEntries(Object.entries(raw).map(([k, v]) => [Number(k), Number(v)]))
}

export function saveSession(session: GameSession): void {
  sessionStorage.setItem(SESSION_KEY(session.game_id), JSON.stringify(session))
}

export function loadSession(gameId: string): GameSession | null {
  const raw = sessionStorage.getItem(SESSION_KEY(gameId))
  if (!raw) return null
  try {
    return JSON.parse(raw) as GameSession
  } catch {
    return null
  }
}
