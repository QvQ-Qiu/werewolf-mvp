import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useGameWebSocket } from '../hooks/useGameWebSocket'
import { useGameStore } from '../stores/gameStore'
import { loadSession } from '../types/game'
import { ROLE_LABEL } from '../lib/labels'
import type { Role } from '../types/game'
import { ActionDock } from '../components/game/ActionDock'
import { GameBoard } from '../components/game/GameBoard'
import { GameHud } from '../components/game/GameHud'
import { ActionFeedbackToast } from '../components/game/ActionFeedbackToast'
import { NpcMindPanel } from '../components/game/NpcMindPanel'
import { GameOverlays } from '../components/game/overlays/GameOverlays'
import { RoleIdentityModal } from '../components/game/overlays/RoleIdentityModal'
import { ErrorState } from '../components/layout/PageState'

export default function GamePage() {
  const navigate = useNavigate()
  const { gameId } = useParams<{ gameId: string }>()
  const session = gameId ? loadSession(gameId) : null
  const { send } = useGameWebSocket(gameId, session?.player_token)

  const {
    yourSeat,
    yourRole,
    phase,
    subPhase,
    dayNumber,
    players,
    publicLog,
    streamingSpeech,
    speechTurn,
    voteActive,
    voteCandidates,
    privateMessages,
    spectatorNote,
    voteSubmitted,
    votePending,
    actionFeedback,
    mindLog,
    filteredView,
  } = useGameStore()

  const [speechText, setSpeechText] = useState('')
  const [voteTarget, setVoteTarget] = useState<number | ''>('')
  const [nightTarget, setNightTarget] = useState<number | ''>('')
  const [identityOpen, setIdentityOpen] = useState(false)

  useEffect(() => {
    if (voteActive && !voteSubmitted) {
      setVoteTarget('')
    }
  }, [voteActive, voteSubmitted, dayNumber])

  if (!gameId || !session) {
    return (
      <ErrorState
        title="未找到对局"
        message="会话已失效，请从大厅重新创建一局。"
        backLabel="返回大厅"
      />
    )
  }

  const self = yourSeat != null ? players.find((p) => p.seat === yourSeat) : null
  const isSpectator = self != null && !self.is_alive
  const roleLabel = ROLE_LABEL[yourRole ?? session.human_role] ?? '未知'
  const resolvedRole = (yourRole ?? session.human_role) as Role | undefined

  const aliveSelf = yourSeat != null && players.find((p) => p.seat === yourSeat)?.is_alive
  const youAreWolf = yourRole === 'wolf' && !!aliveSelf
  const wolfTeammateSeats = youAreWolf ? (filteredView?.wolf_teammates ?? []) : []
  const dockActive =
    isSpectator ||
    (speechTurn?.is_you && !isSpectator) ||
    (voteActive && !!aliveSelf && (voteSubmitted || votePending))

  function handleSubmitSpeech() {
    send('SUBMIT_SPEECH', { content: speechText })
    setSpeechText('')
  }

  function handleSkipSpeech() {
    send('SKIP_SPEECH', {})
  }

  function handleSubmitVote(override?: number | '' | null) {
    if (voteSubmitted || votePending) return
    const target = override !== undefined ? override : voteTarget
    const seat = target === '' || target === null ? null : target
    useGameStore.getState().setVotePending(true)
    useGameStore.getState().setActionFeedback({
      kind: 'vote',
      message: seat == null ? '正在提交弃票…' : `正在投票给 ${seat} 号…`,
      success: true,
    })
    send('SUBMIT_VOTE', { target_seat: seat })
    if (seat != null) setVoteTarget(seat)
  }

  function handleVoteSeat(seat: number) {
    if (!voteActive || voteSubmitted || votePending) return
    setVoteTarget(seat)
  }

  function handleAbstainVote() {
    handleSubmitVote(null)
  }

  function handleNightAction(actionType: string, extra: Record<string, unknown> = {}) {
    useGameStore.getState().setNightActionPending(true)
    send('SUBMIT_NIGHT_ACTION', {
      action_type: actionType,
      target_seat: nightTarget === '' ? null : nightTarget,
      ...extra,
    })
    setNightTarget('')
  }

  function handleLeaveGame() {
    const ok = window.confirm(
      '确定退出当前对局并返回大厅？对局将在后台继续，但你将无法再操作本局。',
    )
    if (!ok) return
    useGameStore.getState().reset()
    navigate('/')
  }

  return (
    <div className="game-viewport">
      {actionFeedback && <ActionFeedbackToast feedback={actionFeedback} />}
      <GameHud onLeave={handleLeaveGame} />

      <div className="game-board-zone">
        <GameBoard
          players={players}
          yourSeat={yourSeat}
          phase={phase}
          subPhase={subPhase}
          dayNumber={dayNumber}
          wolfTeammateSeats={wolfTeammateSeats}
          youAreWolf={youAreWolf}
          speakingSeat={speechTurn?.seat}
          voteActive={voteActive}
          voteTarget={voteTarget}
          voteCandidates={voteCandidates}
          onVoteSelect={setVoteTarget}
          onVoteSeat={handleVoteSeat}
          publicLog={publicLog}
          streamingSpeech={streamingSpeech}
          privateMessages={privateMessages}
          seat={yourSeat ?? session.human_seat}
          role={resolvedRole ?? null}
          roleLabel={roleLabel}
          onShowIdentity={resolvedRole ? () => setIdentityOpen(true) : undefined}
        />
      </div>

      {dockActive && (
        <div className="game-dock">
          <ActionDock
            disabled={isSpectator}
            spectator={isSpectator}
            spectatorNote={spectatorNote}
            speechTurn={speechTurn}
            speechText={speechText}
            onSpeechText={setSpeechText}
            onSubmitSpeech={handleSubmitSpeech}
            onSkipSpeech={handleSkipSpeech}
            voteActive={voteActive}
            yourSeat={yourSeat}
            players={players}
            voteSubmitted={voteSubmitted}
            votePending={votePending}
            compact
          />
        </div>
      )}

      <GameOverlays
        gameId={gameId}
        nightTarget={nightTarget}
        onNightTarget={setNightTarget}
        onNightAction={handleNightAction}
        voteTarget={voteTarget}
        onVoteTarget={setVoteTarget}
        onSubmitVote={() => handleSubmitVote()}
        onAbstainVote={handleAbstainVote}
        onAckSeerResult={() => send('ACK_SEER_CHECK_RESULT', {})}
        disabled={isSpectator}
      />

      <NpcMindPanel entries={mindLog} />

      {identityOpen && resolvedRole && (
        <RoleIdentityModal
          seat={yourSeat ?? session.human_seat}
          role={resolvedRole}
          onClose={() => setIdentityOpen(false)}
        />
      )}
    </div>
  )
}
