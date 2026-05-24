import type { Phase, Role, SubPhase } from '../types/game'

export const PHASE_LABEL: Record<Phase, string> = {
  setup: '准备',
  night: '夜晚',
  day: '白天',
  game_over: '结束',
}

export const SUB_PHASE_LABEL: Record<SubPhase, string> = {
  night_wolf: '狼人行动',
  night_seer: '预言家验人',
  night_witch: '女巫行动',
  night_guard: '守卫守护',
  night_resolve: '夜晚结算',
  day_announce: '公布死讯',
  day_speech: '发言阶段',
  day_vote: '投票阶段',
  day_resolve: '投票结算',
  hunter_shoot: '猎人开枪',
}

export const ROLE_LABEL: Record<Role, string> = {
  wolf: '狼人',
  seer: '预言家',
  witch: '女巫',
  hunter: '猎人',
  guard: '守卫',
  villager: '村民',
}

export const ROLE_HINT: Record<Role, string> = {
  wolf: '夜晚与狼队友商议刀口，你的提名计入狼队表决。',
  seer: '夜晚可验一名存活玩家阵营，结果仅你可见。',
  witch: '拥有一瓶解药与一瓶毒药，每夜最多使用一瓶，也可跳过。',
  hunter: '被放逐或夜间出局时（非毒杀）可开枪带走一人。',
  guard: '夜晚守护一名玩家，不能连续两夜守同一人。',
  villager: '无夜间技能，白天依靠发言与投票帮助好人阵营。',
}

/** 刚进入夜晚（仅一次） */
export const NIGHT_FALL_CUE = {
  title: '天黑请闭眼',
  subtitle: '请保持安静，等待指令…',
}

/** 夜晚各身份行动 — 全员看到「XX请睁眼」 */
export const NIGHT_WAKE_CUE: Record<Role, { title: string; subtitle: string }> = {
  wolf: { title: '狼人请睁眼', subtitle: '与队友商议并提名刀口' },
  seer: { title: '预言家请睁眼', subtitle: '选择一名存活玩家查验' },
  witch: { title: '女巫请睁眼', subtitle: '选择是否使用解药或毒药' },
  hunter: { title: '猎人请睁眼', subtitle: '选择是否开枪' },
  guard: { title: '守卫请睁眼', subtitle: '选择守护目标' },
  villager: { title: '请保持闭眼', subtitle: '等待其他身份行动' },
}

export const NIGHT_ACTION_TITLE: Record<string, string> = {
  wolf_nominate: '狼人 · 提名刀口',
  wolf_kill: '狼人 · 提名刀口',
  seer_check: '预言家 · 查验身份',
  witch_action: '女巫 · 使用药水',
  guard_protect: '守卫 · 选择守护',
  hunter_shoot: '猎人 · 是否开枪',
}

export const PRIVATE_CHANNEL_LABEL: Record<string, string> = {
  seer_result: '验人',
}

export const LOG_TYPE_LABEL: Record<string, string> = {
  system: '系统',
  speech: '发言',
  vote: '投票',
  death: '死讯',
  skill_reveal: '技能',
}
