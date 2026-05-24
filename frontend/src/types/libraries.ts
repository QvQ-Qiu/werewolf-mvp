export interface LibraryListItem {
  id: string
  name: string
  is_builtin: boolean
  personality_count?: number
  strategy_role_count?: number
  updated_at?: string | null
}

export interface PersonalityTemplate {
  id: string
  name: string
  aggression: number
  logic: number
  speech_length?: string
  style_hint: string
  decision_bias: string
  low_logic: boolean
}

export interface PersonalityLibrary {
  id: string
  name: string
  is_builtin: boolean
  personalities: PersonalityTemplate[]
  created_at?: string | null
  updated_at?: string | null
}

export interface StrategyEntry {
  id: string
  role: string
  name: string
  tendency: string
  priority: number
  weight: number
  prompt_hint: string
}

export interface StrategyLibrary {
  id: string
  name: string
  is_builtin: boolean
  strategies_by_role: Record<string, StrategyEntry[]>
  created_at?: string | null
  updated_at?: string | null
}

export const ROLE_OPTIONS = [
  { value: 'wolf', label: '狼人' },
  { value: 'seer', label: '预言家' },
  { value: 'witch', label: '女巫' },
  { value: 'hunter', label: '猎人' },
  { value: 'guard', label: '守卫' },
  { value: 'villager', label: '村民' },
] as const
