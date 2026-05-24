import { useGameCinematic } from '../../../hooks/useGameCinematic'
import { useSubPhaseCue } from '../../../hooks/useSubPhaseCue'
import { useGameStore } from '../../../stores/gameStore'
import { PhaseTransitionOverlay } from './PhaseTransitionOverlay'
import { RoleRevealOverlay } from './RoleRevealOverlay'
import { SkillActionModal } from './SkillActionModal'
import { SubPhaseCueOverlay } from './SubPhaseCueOverlay'
import { GameResultOverlay } from './GameResultOverlay'
import { VoteActionModal } from './VoteActionModal'
import { WolfKillResultOverlay } from './WolfKillResultOverlay'
import { SeerCheckResultOverlay } from './SeerCheckResultOverlay'
import type { Role } from '../../../types/game'

export function GameOverlays({
  gameId,
  nightTarget,
  onNightTarget,
  onNightAction,
  voteTarget,
  onVoteTarget,
  onSubmitVote,
  onAbstainVote,
  onAckSeerResult,
  disabled,
}: {
  gameId: string
  nightTarget: number | ''
  onNightTarget: (v: number | '') => void
  onNightAction: (actionType: string, extra?: Record<string, unknown>) => void
  voteTarget: number | ''
  onVoteTarget: (v: number | '') => void
  onSubmitVote: () => void
  onAbstainVote: () => void
  onAckSeerResult: () => void
  disabled?: boolean
}) {
  const { phaseCue, roleRevealOpen, dismissRoleReveal, yourRole, yourSeat } = useGameCinematic(gameId)
  const subPhaseCue = useSubPhaseCue()
  const nightAction = useGameStore((s) => s.nightAction)
  const nightActionPending = useGameStore((s) => s.nightActionPending)
  const wolfNominations = useGameStore((s) => s.wolfNominations)
  const wolfKillResult = useGameStore((s) => s.wolfKillResult)
  const seerCheckResult = useGameStore((s) => s.seerCheckResult)
  const voteActive = useGameStore((s) => s.voteActive)
  const voteCandidates = useGameStore((s) => s.voteCandidates)
  const voteSubmitted = useGameStore((s) => s.voteSubmitted)
  const votePending = useGameStore((s) => s.votePending)
  const players = useGameStore((s) => s.players)
  const yourSeatStore = useGameStore((s) => s.yourSeat)
  const gameEnded = useGameStore((s) => s.gameEnded)
  const winner = useGameStore((s) => s.winner)
  const setWolfKillResult = useGameStore((s) => s.setWolfKillResult)
  const setSeerCheckResult = useGameStore((s) => s.setSeerCheckResult)

  const seat = yourSeat ?? yourSeatStore
  const aliveSelf = seat != null && players.find((p) => p.seat === seat)?.is_alive
  const isMyNightTurn =
    !!nightAction && nightAction.actor_seat === seat && !!aliveSelf
  const showVote =
    voteActive && !!aliveSelf && !disabled && !voteSubmitted && !votePending
  const showResult = gameEnded && winner != null
  const showSkill = isMyNightTurn && !disabled && !roleRevealOpen && !seerCheckResult
  const showSubPhaseCue = !!subPhaseCue && !roleRevealOpen && !showResult && !showSkill && !showVote

  return (
    <>
      {showResult && winner && (
        <GameResultOverlay gameId={gameId} winner={winner} yourRole={yourRole as Role | null} />
      )}
      {phaseCue && !roleRevealOpen && !showResult && !subPhaseCue && (
        <PhaseTransitionOverlay cue={phaseCue} />
      )}
      {showSubPhaseCue && subPhaseCue && <SubPhaseCueOverlay cue={subPhaseCue} />}
      {roleRevealOpen && yourRole && seat != null && !showResult && (
        <RoleRevealOverlay seat={seat} role={yourRole as Role} onConfirm={dismissRoleReveal} />
      )}
      {showSkill && nightAction && !showResult && (
        <SkillActionModal
          request={nightAction}
          target={nightTarget}
          onTarget={onNightTarget}
          onAction={onNightAction}
          disabled={disabled || nightActionPending}
          pending={nightActionPending}
          wolfNominations={wolfNominations}
        />
      )}
      {showVote && !showResult && (
        <VoteActionModal
          candidates={voteCandidates}
          players={players}
          target={voteTarget}
          onTarget={onVoteTarget}
          onSubmit={onSubmitVote}
          onAbstain={onAbstainVote}
          disabled={disabled}
          pending={votePending}
        />
      )}
      {wolfKillResult && !showResult && (
        <WolfKillResultOverlay
          killTarget={wolfKillResult.killTarget}
          isTie={wolfKillResult.isTie}
          tiedTargets={wolfKillResult.tiedTargets}
          onDismiss={() => setWolfKillResult(null)}
        />
      )}
      {seerCheckResult && !showResult && (
        <SeerCheckResultOverlay
          targetSeat={seerCheckResult.targetSeat}
          resultLabel={seerCheckResult.resultLabel}
          isWolf={seerCheckResult.isWolf}
          onConfirm={() => {
            onAckSeerResult()
            setSeerCheckResult(null)
          }}
        />
      )}
    </>
  )
}
