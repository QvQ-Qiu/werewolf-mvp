import { LOG_TYPE_LABEL, PRIVATE_CHANNEL_LABEL, ROLE_LABEL } from './labels'
import type { PublicLogEntry } from '../types/game'
import type { GameReplayResponse, PlayerDossier, ThoughtEntry, TimelineEvent } from '../types/replay'

const STEP_LABEL: Record<string, string> = {
  select_strategy: '策略选择',
  decide_action: '行动决策',
  generate_speech: '发言生成',
}

function ts(iso: string): number {
  const n = new Date(iso).getTime()
  return Number.isNaN(n) ? 0 : n
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '--:--'
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function phaseRefMeta(phaseRef: string): { round: string; order: number } {
  if (!phaseRef) return { round: '对局', order: 0 }
  const m = phaseRef.match(/^day(\d+)_/)
  const day = m ? Number(m[1]) : 0
  if (phaseRef.includes('night')) return { round: `第 ${day} 夜`, order: day * 2 }
  if (phaseRef.includes('day')) return { round: `第 ${day} 日`, order: day * 2 + 1 }
  return { round: phaseRef, order: day }
}

function phaseRefToRound(phaseRef: string): string {
  return phaseRefMeta(phaseRef).round
}

function traceToKind(step: string): ThoughtEntry['kind'] {
  if (step === 'select_strategy') return 'strategy'
  if (step === 'decide_action') return 'action'
  if (step === 'generate_speech') return 'speech'
  return 'thought'
}

function logToKind(type: string): ThoughtEntry['kind'] {
  if (type === 'speech') return 'speech'
  if (type === 'vote') return 'vote'
  return 'action'
}

export function mapPublicLogToTimeline(entries: PublicLogEntry[]): TimelineEvent[] {
  return entries.map((e) => ({
    id: e.id,
    phase: LOG_TYPE_LABEL[e.type] ?? e.type,
    seat: e.seat,
    content: e.content,
    time: formatTime(e.timestamp),
  }))
}

type Stamped = { at: number; entry: ThoughtEntry }

function collectSeatEntries(
  replay: GameReplayResponse,
  seat: number,
): ThoughtEntry[] {
  const stamped: Stamped[] = []

  for (const t of replay.llm_traces) {
    if (t.player_seat !== seat) continue
    const { round, order } = phaseRefMeta(t.phase_ref || '')
    stamped.push({
      at: ts(t.timestamp),
      entry: {
        id: `trace-${seat}-${t.step}-${t.timestamp}`,
        seat,
        round,
        roundOrder: order,
        kind: traceToKind(t.step),
        label: STEP_LABEL[t.step] ?? t.step,
        content:
          t.step === 'select_strategy' && t.strategy_id
            ? `${t.strategy_id} · ${t.response_summary}`
            : t.response_summary || t.prompt_summary,
      },
    })
  }

  for (const e of replay.public_log) {
    if (e.seat !== seat || e.type === 'system') continue
    stamped.push({
      at: ts(e.timestamp),
      entry: {
        id: `log-${e.id}`,
        seat,
        round: '对局',
        roundOrder: 0,
        kind: logToKind(e.type),
        label: LOG_TYPE_LABEL[e.type] ?? e.type,
        content: e.content,
      },
    })
  }

  for (const m of replay.private_messages) {
    if (!m.visible_to.includes(seat)) continue
    stamped.push({
      at: ts(m.timestamp),
      entry: {
        id: `priv-${m.id}`,
        seat,
        round: phaseRefToRound(m.phase_ref),
        roundOrder: 0,
        kind: 'private',
        label: PRIVATE_CHANNEL_LABEL[m.channel] ?? m.channel,
        content: m.content,
      },
    })
  }

  stamped.sort((a, b) => a.at - b.at)
  return stamped.map((s, i) => ({ ...s.entry, roundOrder: i }))
}

export function mapReplayToDossiers(replay: GameReplayResponse): PlayerDossier[] {
  return replay.players.map((p) => ({
    seat: p.seat,
    name: p.name,
    role: ROLE_LABEL[p.role] ?? p.role,
    alive: p.is_alive,
    personality: p.personality_name ?? undefined,
    entries: collectSeatEntries(replay, p.seat),
  }))
}
