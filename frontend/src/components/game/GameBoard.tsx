import { SeatColumn } from './SeatColumn'
import { PrivateLogPanel } from './PrivateLogPanel'
import { PublicLogPanel } from './PublicLogPanel'
import { IdentitySlot } from './GameHud'
import { PhaseBar } from './PhaseBar'
import type {
  Phase,
  PlayerPublicInfo,
  PrivateMessage,
  PublicLogEntry,
  Role,
  StreamingSpeech,
  SubPhase,
} from '../../types/game'

interface GameBoardProps {
  players: PlayerPublicInfo[]
  yourSeat: number | null
  phase: Phase | null
  subPhase: SubPhase | null
  dayNumber: number
  wolfTeammateSeats?: number[]
  youAreWolf?: boolean
  speakingSeat: number | null | undefined
  voteActive: boolean
  voteTarget: number | ''
  voteCandidates: number[]
  onVoteSelect: (seat: number | '') => void
  onVoteSeat?: (seat: number) => void
  publicLog: PublicLogEntry[]
  streamingSpeech?: StreamingSpeech | null
  privateMessages?: PrivateMessage[]
  seat: number
  role: Role | null
  roleLabel: string
  onShowIdentity?: () => void
}

/** 三列棋盘：左 1–5 · 中公屏（独立滚动）· 右 6–10 */
export function GameBoard({
  players,
  yourSeat,
  phase,
  subPhase,
  dayNumber,
  wolfTeammateSeats = [],
  youAreWolf = false,
  speakingSeat,
  voteActive,
  voteTarget,
  voteCandidates,
  onVoteSelect,
  onVoteSeat,
  publicLog,
  streamingSpeech = null,
  privateMessages = [],
  seat,
  role,
  roleLabel,
  onShowIdentity,
}: GameBoardProps) {
  const aliveCount = players.filter((p) => p.is_alive).length
  const total = players.length

  return (
    <div className="game-board game-frame flex h-full min-h-0 flex-col overflow-hidden">
      <div className="game-board__header flex shrink-0 items-center justify-between gap-2 border-b border-medium px-2 py-1.5 sm:gap-3 sm:px-3 sm:py-2">
        <PhaseBar phase={phase} subPhase={subPhase} dayNumber={dayNumber} dense />
        <div className="game-board__header-end flex shrink-0 items-center gap-2 sm:gap-3">
          <div className="board-alive-stat text-right leading-none">
            <span className="board-stat text-sm sm:text-base">{aliveCount}</span>
            <span className="board-alive-stat__total text-[10px] text-muted">/{total}</span>
          </div>
          <IdentitySlot
            seat={seat}
            role={role}
            roleLabel={roleLabel}
            onShowIdentity={onShowIdentity}
          />
        </div>
      </div>
      <div className="game-board-columns">
        <SeatColumn
          side="left"
          players={players}
          yourSeat={yourSeat}
          wolfTeammateSeats={wolfTeammateSeats}
          youAreWolf={youAreWolf}
          speakingSeat={speakingSeat}
          voteActive={voteActive}
          voteTarget={voteTarget}
          voteCandidates={voteCandidates}
          onVoteSelect={onVoteSelect}
          onVoteSeat={onVoteSeat}
        />
        <PublicLogPanel entries={publicLog} streamingSpeech={streamingSpeech} embedded />
        <SeatColumn
          side="right"
          players={players}
          yourSeat={yourSeat}
          wolfTeammateSeats={wolfTeammateSeats}
          youAreWolf={youAreWolf}
          speakingSeat={speakingSeat}
          voteActive={voteActive}
          voteTarget={voteTarget}
          voteCandidates={voteCandidates}
          onVoteSelect={onVoteSelect}
          onVoteSeat={onVoteSeat}
        />
      </div>
      <PrivateLogPanel messages={privateMessages} />
    </div>
  )
}
