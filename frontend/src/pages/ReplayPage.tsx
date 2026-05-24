import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchGameReplay } from '../api/client'
import { loadReplayCache, saveReplayCache } from '../lib/replayCache'
import { loadSession } from '../types/game'
import type { BeliefStateDto, GameReplayResponse } from '../types/replay'
import { Tabs } from '../components/ui/Tabs'
import { Button } from '../components/ui/Button'
import { ErrorState } from '../components/layout/PageState'
import { cn } from '../lib/cn'
import { mapPublicLogToTimeline, mapReplayToDossiers } from '../lib/replayMapper'
import { winnerFactionLabel } from '../lib/gameOutcome'
import type { PlayerDossier, ThoughtEntry, TimelineEvent } from '../types/replay'

const TAB_ITEMS = [
  { id: 'overview', label: '总览' },
  { id: 'dossier', label: '个体档案' },
]

const KIND_LABEL: Record<ThoughtEntry['kind'], string> = {
  strategy: '策略',
  thought: '思考',
  action: '行动',
  speech: '发言',
  vote: '投票',
  private: '私域',
}

export default function ReplayPage() {
  const { gameId } = useParams<{ gameId: string }>()
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [dossiers, setDossiers] = useState<PlayerDossier[]>([])
  const [winner, setWinner] = useState<string | null>(null)
  const [selectedSeat, setSelectedSeat] = useState(1)
  const [beliefs, setBeliefs] = useState<BeliefStateDto[]>([])
  const [fromCache, setFromCache] = useState(false)

  function applyReplay(replay: GameReplayResponse) {
    setTimeline(mapPublicLogToTimeline(replay.public_log))
    const mapped = mapReplayToDossiers(replay)
    setDossiers(mapped)
    setBeliefs(replay.belief_by_seat ?? [])
    setWinner(replay.winner)
    setSelectedSeat(mapped[0]?.seat ?? replay.human_seat)
  }

  useEffect(() => {
    if (!gameId) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setFromCache(false)
    const token = loadSession(gameId)?.player_token
    fetchGameReplay(gameId, token)
      .then((replay) => {
        if (cancelled) return
        saveReplayCache(gameId, replay)
        applyReplay(replay)
      })
      .catch(() => {
        if (cancelled) return
        const cached = loadReplayCache(gameId)
        if (cached) {
          setFromCache(true)
          applyReplay(cached)
        } else {
          setError('加载复盘失败：对局不存在或服务器已重启（且无本地缓存）')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [gameId])

  const dossier = dossiers.find((d) => d.seat === selectedSeat)

  if (!gameId) {
    return <ErrorState title="无效局号" message="缺少对局 ID" backLabel="返回大厅" />
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl py-16 text-center text-sm text-muted">
        正在载入档案…
      </div>
    )
  }

  if (error) {
    return (
      <ErrorState
        title="无法加载复盘"
        message={
          error.includes('404') || error.includes('不存在')
            ? '对局不存在或服务器已重启（复盘仅存于内存，重启后丢失）。'
            : error
        }
        backLabel="返回大厅"
      />
    )
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5">
      <header>
        <p className="text-flourish mb-1">Chronicle</p>
        <p className="text-eyebrow mb-1">对局复盘</p>
        <h1 className="text-display text-2xl">档案记录</h1>
        <p className="mt-2 text-xs text-muted">
          局号 <span className="font-mono text-mist">{gameId}</span>
          {winner ? (
            <>
              <span className="text-dim"> · </span>
              {winnerFactionLabel(winner as 'wolf' | 'village')} 胜出
            </>
          ) : null}
          {fromCache ? <span className="text-dim"> · 本地缓存</span> : null}
        </p>
      </header>

      <Tabs items={TAB_ITEMS} activeId={tab} onChange={setTab} />

      {tab === 'overview' && <OverviewPanel timeline={timeline} />}
      {tab === 'dossier' && (
        <DossierPanel
          dossiers={dossiers}
          selectedSeat={selectedSeat}
          onSelectSeat={setSelectedSeat}
          dossier={dossier}
          belief={beliefs.find((b) => b.seat === selectedSeat)}
        />
      )}

      <div className="flex justify-center pb-4">
        <Link to="/">
          <Button variant="secondary">返回大厅</Button>
        </Link>
      </div>
    </div>
  )
}

function OverviewPanel({ timeline }: { timeline: TimelineEvent[] }) {
  return (
    <section className="panel-surface p-4 sm:p-5">
      <h2 className="text-display mb-4 text-sm">公屏总览</h2>
      {timeline.length === 0 ? (
        <p className="text-sm text-muted">本局暂无公屏记录。</p>
      ) : (
        <ol className="space-y-4">
          {timeline.map((e) => (
            <li
              key={e.id}
              className="flex gap-3 border-l border-[color-mix(in_oklch,var(--text-muted)_15%,transparent)] pl-3"
            >
              <span className="w-10 shrink-0 font-mono text-[10px] text-muted">{e.time}</span>
              <div>
                <div className="mb-0.5 text-[10px] text-muted">
                  {e.phase}
                  {e.seat != null && <span className="ml-2 text-highlight">{e.seat}号</span>}
                </div>
                <p className="text-sm text-mist">{e.content}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function DossierPanel({
  dossiers,
  selectedSeat,
  onSelectSeat,
  dossier,
  belief,
}: {
  dossiers: PlayerDossier[]
  selectedSeat: number
  onSelectSeat: (seat: number) => void
  dossier: PlayerDossier | undefined
  belief?: BeliefStateDto
}) {
  const grouped = groupByRound(dossier?.entries ?? [])

  return (
    <div className="flex min-h-0 flex-col gap-3 sm:min-h-[360px] sm:flex-row sm:gap-4">
      <nav className="panel-surface dossier-seat-nav flex max-w-full shrink-0 gap-2 overflow-x-auto p-2.5 sm:w-40 sm:flex-col sm:gap-1.5 sm:overflow-x-visible sm:p-2">
        {[...dossiers].sort((a, b) => a.seat - b.seat).map((d) => (
          <button
            key={d.seat}
            type="button"
            onClick={() => onSelectSeat(d.seat)}
            className={cn(
              'dossier-seat-btn focus-ring shrink-0 border text-left',
              selectedSeat === d.seat
                ? 'border-active bg-[var(--bg-accent-wash-strong)] text-mist'
                : 'border-subtle text-muted hover:border-medium hover:text-mist',
              !d.alive && 'opacity-50',
            )}
          >
            <span className="text-display block text-base leading-none">{d.seat}</span>
            <span className="mt-1 block max-w-[5.5rem] truncate text-xs leading-tight sm:max-w-none">
              {d.name}
            </span>
          </button>
        ))}
      </nav>

      <section className="panel-surface min-w-0 flex-1 p-4 sm:p-5">
        {!dossier ? (
          <p className="text-sm text-muted">请选择一名玩家</p>
        ) : (
          <>
            <header className="mb-4 border-b border-[color-mix(in_oklch,var(--text-muted)_12%,transparent)] pb-3">
              <h2 className="text-display text-lg">
                {dossier.seat} 号 · {dossier.name}
              </h2>
              <p className="mt-1 text-xs text-muted">
                {dossier.role}
                {dossier.personality ? ` · ${dossier.personality}` : ''}
                {!dossier.alive ? ' · 已出局' : ''}
              </p>
            </header>
            {belief && (
              <div className="mb-4 rounded-sm border border-subtle bg-[var(--bg-accent-wash)] p-3 text-xs text-muted">
                <p className="text-eyebrow mb-2 text-[10px]">信念链（局后披露）</p>
                {belief.suspects.length > 0 && (
                  <p>
                    怀疑：{belief.suspects.join('、')} 号
                  </p>
                )}
                {belief.trusted.length > 0 && (
                  <p>
                    信任：{belief.trusted.join('、')} 号
                  </p>
                )}
                {belief.open_questions.length > 0 && (
                  <p className="mt-1">待证：{belief.open_questions.join('；')}</p>
                )}
              </div>
            )}
            {dossier.entries.length === 0 ? (
              <p className="text-sm text-muted">
                暂无 AI 追溯或私域记录（未配置 Qwen Key 时为 Mock AI，不产生 llm_traces）。
              </p>
            ) : (
              <ol className="space-y-5">
                {grouped.map(([round, entries]) => (
                  <li key={round}>
                    <h3 className="mb-2 text-xs tracking-wide text-muted">{round}</h3>
                    <ul className="space-y-2 border-l border-[color-mix(in_oklch,var(--text-muted)_15%,transparent)] pl-3">
                      {entries.map((e) => (
                        <li key={e.id} className="text-sm">
                          <span className="text-[10px] uppercase tracking-wide text-muted">
                            {KIND_LABEL[e.kind]}
                          </span>
                          <span className="mx-1.5 text-muted">·</span>
                          <span className="text-muted">{e.label}</span>
                          <p className="mt-0.5 leading-relaxed text-mist">{e.content}</p>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            )}
          </>
        )}
      </section>
    </div>
  )
}

function groupByRound(entries: ThoughtEntry[]): [string, ThoughtEntry[]][] {
  const map = new Map<string, ThoughtEntry[]>()
  for (const e of entries) {
    const list = map.get(e.round) ?? []
    list.push(e)
    map.set(e.round, list)
  }
  return [...map.entries()].sort((a, b) => (a[1][0]?.roundOrder ?? 0) - (b[1][0]?.roundOrder ?? 0))
}
