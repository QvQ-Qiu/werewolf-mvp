import { cn } from '../../lib/cn'
import type { PlayerPublicInfo } from '../../types/game'

function SeatToken({
  player,
  isYou,
  isWolfTeammate,
  youAreWolf,
  isSpeaking,
  voteSelected,
  canVote,
  onSelect,
}: {
  player: PlayerPublicInfo
  isYou: boolean
  isWolfTeammate: boolean
  youAreWolf: boolean
  isSpeaking: boolean
  voteSelected: boolean
  canVote: boolean
  onSelect?: () => void
}) {
  const showWolfBorder = player.is_alive && (isWolfTeammate || (isYou && youAreWolf))
  const showWolfTeammateBadge = isWolfTeammate && player.is_alive && !isYou
  const baseClass = cn(
    'game-seat relative flex h-10 w-10 shrink-0 flex-col items-center justify-center sm:h-11 sm:w-11',
    !player.is_alive && 'game-seat--dead',
    isYou && player.is_alive && 'game-seat--you',
    showWolfBorder && 'game-seat--wolf',
    isSpeaking && player.is_alive && 'game-seat--speak',
    voteSelected && 'game-seat--vote',
    canVote && 'cursor-pointer hover:border-active focus-ring',
  )

  const inner = (
    <>
      {isSpeaking && player.is_alive && (
        <span className="seat-badge seat-badge--top text-highlight">言</span>
      )}
      <span
        className={cn(
          'text-display text-sm leading-none sm:text-base',
          (isSpeaking || isYou || !player.is_alive) && 'mt-0.5',
          !player.is_alive && 'line-through decoration-dim',
        )}
      >
        {player.seat}
      </span>
      {isYou && player.is_alive && (
        <span className="seat-badge seat-badge--bottom text-highlight">我</span>
      )}
      {showWolfTeammateBadge && (
        <span className="seat-badge seat-badge--bottom seat-badge--wolf">队友</span>
      )}
      {!player.is_alive && (
        <span className="seat-badge seat-badge--bottom text-dim">亡</span>
      )}
      {voteSelected && <span className="seat-badge seat-badge--corner" aria-hidden />}
    </>
  )

  const label = `${player.seat} 号 · ${player.name}${
    showWolfTeammateBadge || (isYou && youAreWolf && player.is_alive) ? ' · 狼队友' : ''
  }${!player.is_alive ? '（已出局）' : ''}`

  if (canVote) {
    return (
      <button type="button" onClick={onSelect} title={label} aria-label={`${label}，点击投票`} className={baseClass}>
        {inner}
      </button>
    )
  }

  return (
    <div title={label} aria-label={label} className={baseClass}>
      {inner}
    </div>
  )
}

interface SeatColumnProps {
  players: PlayerPublicInfo[]
  yourSeat: number | null
  wolfTeammateSeats: number[]
  youAreWolf: boolean
  speakingSeat: number | null | undefined
  voteActive: boolean
  voteTarget: number | ''
  voteCandidates: number[]
  onVoteSelect: (seat: number | '') => void
  onVoteSeat?: (seat: number) => void
  side: 'left' | 'right'
}

export function SeatColumn(props: SeatColumnProps) {
  const {
    players,
    yourSeat,
    wolfTeammateSeats,
    youAreWolf,
    speakingSeat,
    voteActive,
    voteTarget,
    voteCandidates,
    onVoteSelect,
    onVoteSeat,
    side,
  } = props
  const wolfTeammateSet = new Set(wolfTeammateSeats)
  const sorted = [...players].sort((a, b) => a.seat - b.seat)
  const half = Math.ceil(sorted.length / 2)
  const seats = side === 'left' ? sorted.slice(0, half) : sorted.slice(half)
  const colLabel = side === 'left' ? '1–5' : '6–10'
  const aliveInCol = seats.filter((p) => p.is_alive).length

  return (
    <aside
      className={cn(
        'seat-column',
        side === 'left' ? 'border-r border-medium' : 'border-l border-medium',
      )}
      aria-label={side === 'left' ? '1至5号座位' : '6至10号座位'}
    >
      <div className="seat-column__head shrink-0">
        <span className="seat-col-label block leading-tight">{colLabel}</span>
        <span className="board-stat text-[10px] leading-tight">{aliveInCol}存</span>
        {voteActive && (
          <span className="mt-0.5 block text-[8px] leading-tight text-warm">可投</span>
        )}
      </div>
      <div className="seat-column__seats">
        {seats.map((p) => {
          const canVote = voteActive && voteCandidates.includes(p.seat) && p.seat !== yourSeat && p.is_alive
          return (
            <SeatToken
              key={p.seat}
              player={p}
              isYou={p.seat === yourSeat}
              isWolfTeammate={wolfTeammateSet.has(p.seat)}
              youAreWolf={youAreWolf}
              isSpeaking={p.seat === speakingSeat}
              voteSelected={voteTarget === p.seat}
              canVote={canVote}
              onSelect={() => {
                if (onVoteSeat && canVote) {
                  onVoteSeat(p.seat)
                  return
                }
                onVoteSelect(voteTarget === p.seat ? '' : p.seat)
              }}
            />
          )
        })}
      </div>
    </aside>
  )
}
