import { Eye, Mic, Vote } from 'lucide-react'
import { Button } from '../ui/Button'
import { Countdown } from './Countdown'
import type { PlayerPublicInfo } from '../../types/game'

interface ActionDockProps {
  disabled: boolean
  spectator: boolean
  spectatorNote?: string | null
  speechTurn: { is_you: boolean; deadline_ts?: number } | null
  speechText: string
  onSpeechText: (v: string) => void
  onSubmitSpeech: () => void
  onSkipSpeech: () => void
  voteActive: boolean
  yourSeat: number | null
  players: PlayerPublicInfo[]
  voteSubmitted?: boolean
  votePending?: boolean
  compact?: boolean
}

export function ActionDock(props: ActionDockProps) {
  const {
    disabled,
    spectator,
    spectatorNote,
    speechTurn,
    speechText,
    onSpeechText,
    onSubmitSpeech,
    onSkipSpeech,
    voteActive,
    yourSeat,
    players,
    voteSubmitted = false,
    votePending = false,
    compact = false,
  } = props

  const box = compact ? 'px-2.5 py-3' : 'panel-surface p-4'

  const aliveSelf = yourSeat != null && players.find((p) => p.seat === yourSeat)?.is_alive
  const showSpeech = speechTurn?.is_you && !disabled
  const showVoteStatus = voteActive && aliveSelf && (voteSubmitted || votePending)

  if (spectator && !showSpeech && !showVoteStatus) {
    return (
      <div className={`${box} flex items-center gap-2.5`}>
        <Eye className="h-5 w-5 shrink-0 text-warm" aria-hidden />
        <div>
          <p className="dock-section-title text-sm">观战</p>
          <p className="text-xs text-muted">
            {spectatorNote ?? '可继续查看公屏与左右座位存活'}
          </p>
        </div>
      </div>
    )
  }

  if (!showSpeech && !showVoteStatus) return null

  return (
    <div className="space-y-3">
      {voteActive && votePending && aliveSelf && (
        <div className={`${box} flex items-center gap-2 text-sm text-muted`} role="status">
          <Vote className="h-4 w-4 shrink-0 animate-pulse" aria-hidden />
          <span>正在提交投票…</span>
        </div>
      )}
      {voteActive && voteSubmitted && aliveSelf && !votePending && (
        <div className={`${box} flex items-center gap-2 text-sm text-warm`} role="status">
          <Vote className="h-4 w-4 shrink-0" aria-hidden />
          <span>投票已提交，等待计票…</span>
        </div>
      )}
      {spectator && (
        <div className="flex items-center gap-2 border border-subtle bg-[var(--bg-accent-wash)] px-3 py-2 text-xs text-muted">
          <Eye className="h-4 w-4 text-warm" /> 观战模式
        </div>
      )}

      {showSpeech && (
        <section className={box}>
          <h3 className="mb-3 flex flex-wrap items-center gap-x-2 gap-y-1">
            <Mic className="h-4 w-4 shrink-0 text-highlight" />
            <span className="dock-section-title shrink-0">轮到你发言</span>
            {speechTurn?.deadline_ts ? (
              <span className="text-xs text-muted sm:ml-auto">
                剩余 <Countdown deadlineTs={speechTurn.deadline_ts} />
              </span>
            ) : null}
          </h3>
          <textarea
            className="input-field focus-ring mb-3 max-h-[30vh] min-h-[4.5rem] resize-y px-3 py-2 text-sm"
            rows={2}
            placeholder="输入发言内容…"
            value={speechText}
            onChange={(e) => onSpeechText(e.target.value)}
            disabled={disabled}
          />
          <div className="flex flex-wrap gap-2">
            <Button onClick={onSubmitSpeech} disabled={disabled}>
              提交发言
            </Button>
            <Button variant="secondary" onClick={onSkipSpeech} disabled={disabled}>
              跳过
            </Button>
          </div>
        </section>
      )}
    </div>
  )
}
