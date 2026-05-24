import { create } from 'zustand'
import type { SubPhaseCueView } from '../lib/subPhaseCue'
import type { MindLogEntry } from '../lib/formatMindLog'
import type {
  FilteredPlayerView,
  NightActionRequest,
  Phase,
  PlayerPublicInfo,
  PrivateMessage,
  PublicLogEntry,
  Role,
  SpeechTurn,
  StreamingSpeech,
  SubPhase,
} from '../types/game'
import { normalizeSeatMap } from '../types/game'

export type WsStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'

export type ActionFeedback = {
  kind: 'night' | 'vote' | 'speech'
  message: string
  success: boolean
}

interface GameStore {
  wsStatus: WsStatus
  wsError: string | null
  yourSeat: number | null
  yourRole: Role | null
  phase: Phase | null
  subPhase: SubPhase | null
  dayNumber: number
  players: PlayerPublicInfo[]
  publicLog: PublicLogEntry[]
  streamingSpeech: StreamingSpeech | null
  speechTurn: SpeechTurn | null
  voteActive: boolean
  voteCandidates: number[]
  nightAction: NightActionRequest | null
  nightActionPending: boolean
  voteSubmitted: boolean
  votePending: boolean
  actionFeedback: ActionFeedback | null
  subPhaseCue: SubPhaseCueView | null
  privateMessages: PrivateMessage[]
  filteredView: FilteredPlayerView | null
  gameDeadlineTs: number | null
  spectatorNote: string | null
  winner: 'wolf' | 'village' | null
  gameEnded: boolean
  mindLog: MindLogEntry[]

  wolfNominations: Record<number, number>
  wolfKillResult: {
    killTarget: number
    isTie: boolean
    tiedTargets: number[]
  } | null
  seerCheckResult: {
    targetSeat: number
    isWolf: boolean
    resultLabel: string
  } | null

  setWsStatus: (status: WsStatus, error?: string | null) => void
  applySnapshot: (payload: {
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
  }) => void
  setGameStarted: (
    yourSeat: number,
    yourRole: Role,
    players: PlayerPublicInfo[],
    gameDeadlineTs?: number,
  ) => void
  setPhase: (phase: Phase, dayNumber: number, subPhase?: SubPhase) => void
  appendLog: (entry: PublicLogEntry) => void
  startStreamingSpeech: (seat: number) => void
  appendStreamingSpeech: (seat: number, delta: string) => void
  endStreamingSpeech: (seat: number) => void
  setSpeechTurn: (turn: SpeechTurn | null) => void
  setVoteStarted: (candidates: number[]) => void
  setNightAction: (req: NightActionRequest | null) => void
  setNightActionPending: (pending: boolean) => void
  setVoteSubmitted: (submitted: boolean) => void
  setVotePending: (pending: boolean) => void
  setActionFeedback: (feedback: ActionFeedback | null) => void
  setSubPhaseCue: (cue: SubPhaseCueView | null) => void
  appendPrivateMessage: (msg: PrivateMessage) => void
  appendMindLog: (entry: MindLogEntry) => void
  setWolfNominations: (nominations: Record<number, number>) => void
  setWolfKillResult: (
    result: { killTarget: number; isTie: boolean; tiedTargets: number[] } | null,
  ) => void
  setSeerCheckResult: (
    result: { targetSeat: number; isWolf: boolean; resultLabel: string } | null,
  ) => void
  setSpectatorNote: (note: string | null) => void
  setGameEnd: (winner: 'wolf' | 'village') => void
  reset: () => void
}

const initialState = {
  wsStatus: 'idle' as WsStatus,
  wsError: null,
  yourSeat: null,
  yourRole: null,
  phase: null,
  subPhase: null,
  dayNumber: 0,
  players: [] as PlayerPublicInfo[],
  publicLog: [] as PublicLogEntry[],
  streamingSpeech: null,
  speechTurn: null,
  voteActive: false,
  voteCandidates: [] as number[],
  nightAction: null,
  nightActionPending: false,
  voteSubmitted: false,
  votePending: false,
  actionFeedback: null,
  subPhaseCue: null,
  privateMessages: [] as PrivateMessage[],
  filteredView: null,
  gameDeadlineTs: null,
  spectatorNote: null,
  winner: null,
  gameEnded: false,
  mindLog: [] as MindLogEntry[],
  wolfNominations: {} as Record<number, number>,
  wolfKillResult: null as {
    killTarget: number
    isTie: boolean
    tiedTargets: number[]
  } | null,
  seerCheckResult: null as {
    targetSeat: number
    isWolf: boolean
    resultLabel: string
  } | null,
}

function mergeViewPrivateMessages(
  existing: PrivateMessage[],
  view: FilteredPlayerView | undefined,
): PrivateMessage[] {
  if (!view?.private_messages?.length) return existing
  const added = view.private_messages.map((m, i) => ({
    id: `view-${i}-${m.phase_ref}`,
    channel: m.channel,
    sender_seat: m.sender,
    receiver_seat: view.your_seat ?? 0,
    content: m.content,
    phase_ref: m.phase_ref,
    timestamp: new Date().toISOString(),
  }))
  const ids = new Set(existing.map((x) => x.id))
  return [...existing, ...added.filter((m) => !ids.has(m.id))].slice(-30)
}

export const useGameStore = create<GameStore>((set) => ({
  ...initialState,

  setWsStatus: (status, error = null) => set({ wsStatus: status, wsError: error }),

  applySnapshot: (payload) =>
    set((s) => ({
      phase: payload.phase,
      subPhase: payload.sub_phase,
      dayNumber: payload.day_number,
      players: payload.players,
      publicLog: payload.public_log,
      voteActive: payload.vote_active,
      winner: payload.winner,
      filteredView: payload.filtered_view ?? s.filteredView,
      privateMessages: mergeViewPrivateMessages(s.privateMessages, payload.filtered_view),
      speechTurn: payload.speech_turn
        ? {
            seat: payload.speech_turn.seat,
            deadline_ts: 0,
            is_you: payload.speech_turn.is_you,
          }
        : null,
      spectatorNote: payload.spectator_mode
        ? (payload.filtered_view?.note ?? s.spectatorNote ?? '你已出局，可观战；完整复盘见局后')
        : s.spectatorNote,
    })),

  setGameStarted: (yourSeat, yourRole, players, gameDeadlineTs) =>
    set({ yourSeat, yourRole, players, gameDeadlineTs: gameDeadlineTs ?? null }),

  setPhase: (phase, dayNumber, subPhase) =>
    set({
      phase,
      dayNumber,
      subPhase: subPhase ?? null,
      nightAction: null,
      nightActionPending: false,
      voteSubmitted: false,
      votePending: false,
      wolfNominations: {},
      wolfKillResult: null,
      seerCheckResult: null,
    }),

  appendLog: (entry) =>
    set((s) => {
      if (s.publicLog.some((e) => e.id === entry.id)) return s
      const dropStream =
        s.streamingSpeech != null &&
        entry.type === 'speech' &&
        entry.seat === s.streamingSpeech.seat
      return {
        publicLog: [...s.publicLog, entry],
        streamingSpeech: dropStream ? null : s.streamingSpeech,
      }
    }),

  startStreamingSpeech: (seat) => set({ streamingSpeech: { seat, content: '' } }),

  appendStreamingSpeech: (seat, delta) =>
    set((s) => {
      if (!s.streamingSpeech || s.streamingSpeech.seat !== seat) {
        return { streamingSpeech: { seat, content: delta } }
      }
      return {
        streamingSpeech: {
          seat,
          content: s.streamingSpeech.content + delta,
        },
      }
    }),

  endStreamingSpeech: (seat) =>
    set((s) =>
      s.streamingSpeech?.seat === seat ? { streamingSpeech: null } : s,
    ),

  setSpeechTurn: (turn) => set({ speechTurn: turn }),

  setVoteStarted: (candidates) =>
    set({
      voteActive: true,
      voteCandidates: candidates,
      voteSubmitted: false,
      votePending: false,
    }),

  setNightAction: (req) =>
    set({
      nightAction: req,
      nightActionPending: false,
      wolfNominations: req?.wolf_nominations ? normalizeSeatMap(req.wolf_nominations) : {},
    }),

  setNightActionPending: (pending) => set({ nightActionPending: pending }),

  setVoteSubmitted: (submitted) => set({ voteSubmitted: submitted }),

  setVotePending: (pending) => set({ votePending: pending }),

  setActionFeedback: (feedback) => set({ actionFeedback: feedback }),

  setSubPhaseCue: (cue) => set({ subPhaseCue: cue }),

  appendPrivateMessage: (msg) =>
    set((s) => {
      if (s.privateMessages.some((m) => m.id === msg.id)) return s
      return { privateMessages: [...s.privateMessages, msg].slice(-30) }
    }),

  appendMindLog: (entry) =>
    set((s) => {
      if (s.mindLog.some((e) => e.id === entry.id)) return s
      const next = [...s.mindLog, entry].sort((a, b) => a.at - b.at)
      return { mindLog: next.slice(-200) }
    }),

  setWolfNominations: (nominations) => set({ wolfNominations: nominations }),

  setWolfKillResult: (result) => set({ wolfKillResult: result }),

  setSeerCheckResult: (result) => set({ seerCheckResult: result }),

  setSpectatorNote: (note) => set({ spectatorNote: note }),

  setGameEnd: (winner) =>
    set({
      winner,
      gameEnded: true,
      voteActive: false,
      speechTurn: null,
      streamingSpeech: null,
      nightAction: null,
      nightActionPending: false,
      subPhaseCue: null,
    }),

  reset: () => set(initialState),
}))
