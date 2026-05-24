import { Link } from 'react-router-dom'
import { cn } from '../../../lib/cn'
import { playerOutcome, winnerFactionLabel } from '../../../lib/gameOutcome'
import { ROLE_LABEL } from '../../../lib/labels'
import type { Role } from '../../../types/game'
import { Button } from '../../ui/Button'

export function GameResultOverlay({
  gameId,
  winner,
  yourRole,
}: {
  gameId: string
  winner: 'wolf' | 'village'
  yourRole: Role | null
}) {
  const outcome = playerOutcome(yourRole, winner)
  const isVictory = outcome === 'victory'
  const faction = winnerFactionLabel(winner)
  const roleLabel = yourRole ? ROLE_LABEL[yourRole] : null

  return (
    <div
      className={cn(
        'cinematic-layer cinematic-layer--result',
        isVictory ? 'cinematic-result--victory' : 'cinematic-result--defeat',
      )}
      role="dialog"
      aria-modal="true"
      aria-labelledby="game-result-title"
    >
      <div className={cn('cinematic-result-card', isVictory ? 'cinematic-result-card--win' : 'cinematic-result-card--lose')}>
        <p className="text-flourish text-flourish--lg mb-1">{isVictory ? 'Victory' : 'Defeat'}</p>
        <p className="text-eyebrow mb-2">对局终局</p>
        <h2 id="game-result-title" className={cn('cinematic-result-title', isVictory && 'cinematic-result-title--pulse')}>
          {isVictory ? '胜利' : '败北'}
        </h2>
        <p className="mt-2 text-sm font-light text-mist">
          {faction}胜出
          {roleLabel ? (
            <>
              <span className="text-dim"> · </span>
              你的身份 · {roleLabel}
            </>
          ) : null}
        </p>
        <p className="mt-3 text-xs leading-relaxed text-muted">
          {isVictory
            ? '你在本局中与阵营一同达成了胜利条件。'
            : '本局胜负已分，复盘可回顾每一步推理与发言。'}
        </p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Link to={`/replay/${gameId}`} className="sm:flex-1">
            <Button size="lg" className="w-full">
              查看复盘
            </Button>
          </Link>
          <Link to="/" className="sm:flex-1">
            <Button variant="secondary" size="lg" className="w-full">
              返回大厅
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
