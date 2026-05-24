import { useEffect, useRef } from 'react'
import { fetchGameReplay } from '../api/client'
import { saveReplayCache } from '../lib/replayCache'
import { formatMindLogFromPublicLog, formatMindLogFromTrace } from '../lib/formatMindLog'
import { buildSubPhaseCue } from '../lib/subPhaseCue'
import { useGameStore } from '../stores/gameStore'
import type { GameSession, WsServerEvent } from '../types/game'
import { loadSession, normalizeSeatMap } from '../types/game'

const FEEDBACK_DISMISS_MS = 2800

const RECONNECT_DELAY_MS = 2000
const PING_INTERVAL_MS = 25_000

function buildWsUrl(gameId: string, token: string, session: GameSession | null): string {
  const path =
    session?.ws_url ?? `/ws/games/${gameId}?token=${encodeURIComponent(token)}`
  if (path.startsWith('ws://') || path.startsWith('wss://')) return path
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}${path.startsWith('/') ? path : `/${path}`}`
}

export function useGameWebSocket(gameId: string | undefined, token: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef = useRef(true)
  const sendRef = useRef<(type: string, payload?: Record<string, unknown>) => void>(() => {})

  useEffect(() => {
    if (!gameId || !token) return
    const gid = gameId
    const tok = token

    mountedRef.current = true
    const session = loadSession(gid)
    const store = useGameStore.getState()
    store.reset()
    store.setWsStatus('connecting')

    function send(type: string, payload: Record<string, unknown> = {}) {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type, payload }))
      }
    }
    sendRef.current = send

    function connect() {
      const url = buildWsUrl(gid, tok, session)
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        if (!mountedRef.current) return
        useGameStore.getState().setWsStatus('connected')
        if (pingRef.current) clearInterval(pingRef.current)
        pingRef.current = setInterval(() => send('PING', {}), PING_INTERVAL_MS)
      }

      ws.onmessage = (ev) => {
        if (!mountedRef.current) return
        try {
          const event = JSON.parse(ev.data) as WsServerEvent
          handleEvent(event)
        } catch {
          /* ignore */
        }
      }

      ws.onerror = () => {
        if (!mountedRef.current) return
        useGameStore.getState().setWsStatus('error', 'WebSocket 连接错误')
      }

      ws.onclose = () => {
        if (pingRef.current) {
          clearInterval(pingRef.current)
          pingRef.current = null
        }
        if (!mountedRef.current) return
        const ended = useGameStore.getState().gameEnded
        if (ended) {
          useGameStore.getState().setWsStatus('disconnected')
          return
        }
        useGameStore.getState().setWsStatus('disconnected', '连接已断开，正在重连…')
        reconnectRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    async function cacheReplay() {
      try {
        const replay = await fetchGameReplay(gid, tok)
        saveReplayCache(gid, replay)
      } catch {
        /* 局终缓存失败可忽略 */
      }
    }

    function handleEvent(event: WsServerEvent) {
      const s = useGameStore.getState()
      switch (event.type) {
        case 'CONNECTED':
          break
        case 'GAME_STARTED':
          s.setGameStarted(
            event.payload.your_seat,
            event.payload.your_role,
            event.payload.players,
            event.payload.game_deadline_ts,
          )
          break
        case 'GAME_TIMEOUT':
          useGameStore.getState().setWsStatus('error', event.payload.message)
          break
        case 'PHASE_CHANGED':
          s.setPhase(event.payload.phase, event.payload.day_number, event.payload.sub_phase)
          if (event.payload.sub_phase !== 'day_vote') {
            useGameStore.setState({ voteActive: false, voteSubmitted: false })
          }
          if (event.payload.sub_phase !== 'day_speech') {
            s.setSpeechTurn(null)
          }
          break
        case 'SUB_PHASE_CUE': {
          const yourRole = useGameStore.getState().yourRole
          const view = buildSubPhaseCue(event.payload, yourRole)
          if (view) s.setSubPhaseCue(view)
          break
        }
        case 'ACTION_ACK': {
          const seat = useGameStore.getState().yourSeat
          if (seat == null || event.payload.seat !== seat) break
          s.setActionFeedback({
            kind: event.payload.kind,
            message: event.payload.message,
            success: event.payload.success,
          })
          if (event.payload.kind === 'night') {
            s.setNightAction(null)
            s.setNightActionPending(false)
          }
          if (event.payload.kind === 'vote') {
            s.setVotePending(false)
            if (event.payload.success) {
              s.setVoteSubmitted(true)
            }
          }
          window.setTimeout(() => {
            const cur = useGameStore.getState().actionFeedback
            if (cur?.message === event.payload.message) {
              useGameStore.getState().setActionFeedback(null)
            }
          }, FEEDBACK_DISMISS_MS)
          break
        }
        case 'PUBLIC_LOG': {
          s.appendLog(event.payload.entry)
          const mind = formatMindLogFromPublicLog(event.payload.entry)
          if (mind) s.appendMindLog(mind)
          break
        }
        case 'LLM_TRACE':
          s.appendMindLog(formatMindLogFromTrace(event.payload))
          break
        case 'SPEECH_STREAM_START':
          s.startStreamingSpeech(event.payload.seat)
          break
        case 'SPEECH_STREAM_DELTA':
          s.appendStreamingSpeech(event.payload.seat, event.payload.delta)
          break
        case 'SPEECH_STREAM_END':
          s.endStreamingSpeech(event.payload.seat)
          break
        case 'SPEAK_TURN_START':
          s.setSpeechTurn(event.payload)
          break
        case 'SPEAK_TURN_END':
          s.setSpeechTurn(null)
          s.endStreamingSpeech(event.payload.seat)
          break
        case 'VOTE_STARTED':
          s.setVoteStarted(event.payload.candidates)
          useGameStore.setState({ voteSubmitted: false })
          break
        case 'WOLF_NOMINATION_UPDATE': {
          const nominations = normalizeSeatMap(event.payload.nominations)
          s.setWolfNominations(nominations)
          if (s.nightAction?.action_type === 'wolf_nominate') {
            s.setNightAction({
              ...s.nightAction,
              wolf_nominations: nominations,
              wolf_teammates: event.payload.teammates,
            })
          }
          break
        }
        case 'WOLF_KILL_RESULT':
          s.setWolfKillResult({
            killTarget: event.payload.kill_target,
            isTie: event.payload.is_tie,
            tiedTargets: event.payload.tied_targets,
          })
          break
        case 'SEER_CHECK_RESULT':
          s.setSeerCheckResult({
            targetSeat: event.payload.target_seat,
            isWolf: event.payload.is_wolf,
            resultLabel: event.payload.result_label,
          })
          break
        case 'VOTE_RESULT': {
          const eliminated = event.payload.eliminated_seat
          useGameStore.setState({ voteActive: false, voteCandidates: [] })
          if (eliminated != null) {
            useGameStore.setState((state) => ({
              players: state.players.map((p) =>
                p.seat === eliminated ? { ...p, is_alive: false } : p,
              ),
            }))
          }
          break
        }
        case 'SPECTATOR_MODE':
          s.setSpectatorNote(event.payload.message)
          break
        case 'PRIVATE_MESSAGE':
          s.appendPrivateMessage(event.payload)
          break
        case 'NIGHT_ACTION_REQUEST':
          s.setNightAction(event.payload)
          break
        case 'STATE_SNAPSHOT':
          s.applySnapshot(event.payload)
          break
        case 'GAME_END':
          s.setGameEnd(event.payload.winner)
          void cacheReplay()
          break
        case 'ERROR': {
          const code = event.payload.code
          const msg = event.payload.message
          if (
            code === 'NOT_VOTE_PHASE' ||
            code === 'ALREADY_VOTED' ||
            code === 'NOT_ALIVE' ||
            code === 'EMPTY_MESSAGE'
          ) {
            s.setVotePending(false)
            s.setActionFeedback({ kind: 'vote', message: msg, success: false })
            window.setTimeout(() => {
              const cur = useGameStore.getState().actionFeedback
              if (cur?.message === msg) {
                useGameStore.getState().setActionFeedback(null)
              }
            }, FEEDBACK_DISMISS_MS)
          } else {
            useGameStore.getState().setWsStatus('error', msg)
          }
          break
        }
      }
    }

    connect()

    return () => {
      mountedRef.current = false
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      if (pingRef.current) clearInterval(pingRef.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [gameId, token]) // gid/tok narrowed above

  function send(type: string, payload: Record<string, unknown> = {}) {
    sendRef.current(type, payload)
  }

  return { send }
}
