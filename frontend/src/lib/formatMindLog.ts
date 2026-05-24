import { ROLE_LABEL } from './labels'
import type { Role } from '../types/game'

export type MindLogKind = 'llm' | 'system'

export interface MindLogEntry {
  id: string
  kind: MindLogKind
  at: number
  seat?: number
  role?: Role | string
  step?: string
  phaseRef?: string
  promptText: string
  responseText: string
  summary: string
}

const STEP_LABEL: Record<string, string> = {
  select_strategy: '策略选择',
  decide_action: '行动决策',
  generate_speech: '发言生成',
}

function parseJson(text: string): Record<string, unknown> | null {
  try {
    return JSON.parse(text.trim()) as Record<string, unknown>
  } catch {
    return null
  }
}

export function messagesToPromptText(messages: { role: string; content: string }[]): string {
  if (!messages?.length) return '（无提示词记录）'
  return messages.map((m) => `[${m.role}]\n${m.content}`).join('\n\n')
}

export function summarizeLlmResponse(
  step: string,
  response: string,
  phaseRef?: string,
): string {
  if (step === 'generate_speech') {
    const t = response.trim()
    return t ? `发言：${t.length > 160 ? `${t.slice(0, 160)}…` : t}` : '发言：（空）'
  }
  const data = parseJson(response)
  if (!data) {
    return response.trim().slice(0, 200) || '（无输出）'
  }
  if (step === 'select_strategy') {
    const sid = data.strategy_id ?? ''
    const reason = data.reason ?? ''
    return `选择策略 ${sid}${reason ? `：${reason}` : ''}`
  }
  const at = String(data.action_type ?? '')
  const target = data.target_seat as number | null | undefined
  const extra = (data.extra ?? {}) as Record<string, unknown>

  switch (at) {
    case 'wolf_nominate':
    case 'wolf_kill':
      return target != null ? `选择刀 ${target} 号` : '狼刀（未指定目标）'
    case 'seer_check':
      return target != null ? `查验 ${target} 号` : '验人（未指定）'
    case 'witch_heal':
      return target != null ? `使用解药救 ${target} 号` : '使用解药'
    case 'witch_poison':
      return target != null ? `毒 ${target} 号` : '使用毒药'
    case 'guard_protect':
      return target != null ? `守护 ${target} 号` : '守护（未指定）'
    case 'hunter_shoot':
      return target != null ? `开枪带 ${target} 号` : '开枪（未指定）'
    case 'vote':
      return target != null ? `投票 ${target} 号` : '弃票'
    case 'pass':
      if (phaseRef?.includes('witch')) {
        if (extra.use_heal === false || extra.use_poison === false) {
          if (extra.use_heal === false) return '不使用解药'
          return '不使用毒药'
        }
        return '女巫跳过'
      }
      return '跳过'
    default:
      return JSON.stringify(data)
  }
}

export function formatMindLogFromTrace(payload: {
  trace_id?: string
  player_seat: number
  role: string
  step: string
  phase_ref?: string
  messages: { role: string; content: string }[]
  response: string
  strategy_id?: string | null
  timestamp: string
}): MindLogEntry {
  const roleKey = payload.role as Role
  const roleLabel = ROLE_LABEL[roleKey] ?? payload.role
  const stepLabel = STEP_LABEL[payload.step] ?? payload.step
  const promptText = messagesToPromptText(payload.messages)
  const responseText = payload.response?.trim() ?? ''
  const summary = summarizeLlmResponse(payload.step, responseText, payload.phase_ref)
  const at = new Date(payload.timestamp).getTime()

  return {
    id:
      payload.trace_id ??
      `llm-${payload.player_seat}-${payload.step}-${payload.timestamp}`,
    kind: 'llm',
    at: Number.isNaN(at) ? Date.now() : at,
    seat: payload.player_seat,
    role: roleLabel,
    step: stepLabel,
    phaseRef: payload.phase_ref,
    promptText,
    responseText,
    summary: `${payload.player_seat}号<${roleLabel}> · ${stepLabel} → ${summary}`,
  }
}

export function formatMindLogFromPublicLog(entry: {
  id: string
  type: string
  seat?: number | null
  content: string
  timestamp: string
}): MindLogEntry | null {
  if (entry.type !== 'death' && entry.type !== 'system') return null
  const at = new Date(entry.timestamp).getTime()
  return {
    id: `log-${entry.id}`,
    kind: 'system',
    at: Number.isNaN(at) ? Date.now() : at,
    promptText: '',
    responseText: '',
    summary: entry.content,
  }
}
