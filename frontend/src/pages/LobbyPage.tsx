import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BookOpen, Brain, ChevronDown, Sparkles } from 'lucide-react'
import { checkHealth, createGame, listPersonalityLibraries, listStrategyLibraries } from '../api/client'
import { loadLobbyLibraryPrefs, saveLobbyLibraryPrefs } from '../lib/lobbyPrefs'
import { libraryOptionLabel } from '../lib/libraryLabels'
import type { LibraryListItem } from '../types/libraries'
import { Button } from '../components/ui/Button'
import { Collapse } from '../components/ui/Collapse'
import { Input } from '../components/ui/Input'
import { SelectField } from '../components/ui/SelectField'

export default function LobbyPage() {
  const navigate = useNavigate()
  const [playerName, setPlayerName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)
  const [llmOk, setLlmOk] = useState<boolean | null>(null)
  const [llmError, setLlmError] = useState<string | null>(null)
  const [personalityLibs, setPersonalityLibs] = useState<LibraryListItem[]>([])
  const [strategyLibs, setStrategyLibs] = useState<LibraryListItem[]>([])
  const [personalityLibId, setPersonalityLibId] = useState(() => loadLobbyLibraryPrefs().personalityLibId)
  const [strategyLibId, setStrategyLibId] = useState(() => loadLobbyLibraryPrefs().strategyLibId)

  useEffect(() => {
    checkHealth().then(({ ok, llm }) => {
      setBackendOk(ok)
      if (!llm) {
        setLlmOk(null)
        setLlmError(null)
        return
      }
      setLlmOk(llm.configured ? llm.reachable : null)
      setLlmError(llm.configured && !llm.reachable ? llm.error ?? 'LLM 不可达' : null)
    })
  }, [])

  useEffect(() => {
    void Promise.all([listPersonalityLibraries(), listStrategyLibraries()])
      .then(([p, s]) => {
        setPersonalityLibs(p)
        setStrategyLibs(s)
        setPersonalityLibId((cur) => (p.some((x) => x.id === cur) ? cur : (p[0]?.id ?? 'default')))
        setStrategyLibId((cur) => (s.some((x) => x.id === cur) ? cur : (s[0]?.id ?? 'default')))
      })
      .catch(() => {
        /* 库列表加载失败不阻塞开局 */
      })
  }, [])

  useEffect(() => {
    saveLobbyLibraryPrefs({ personalityLibId, strategyLibId })
  }, [personalityLibId, strategyLibId])

  async function handleCreate() {
    if (!playerName.trim()) {
      setError('请输入昵称')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const { game_id } = await createGame(playerName.trim(), {
        personalityLibraryId: personalityLibId,
        strategyLibraryId: strategyLibId,
      })
      navigate(`/game/${game_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建对局失败，请确认后端已启动')
    } finally {
      setLoading(false)
    }
  }

  const personalityOptions = personalityLibs.map((item) => ({
    value: item.id,
    label: libraryOptionLabel(item),
  }))

  const strategyOptions = strategyLibs.map((item) => ({
    value: item.id,
    label: libraryOptionLabel(item),
  }))

  return (
    <div className="mx-auto max-w-3xl">
      <div className="lobby-sheet">
        <section className="lobby-section lobby-hero relative overflow-hidden">
          <p className="text-flourish text-flourish--lg mb-1">The Gathering</p>
          <p className="text-eyebrow mb-2 flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-warm" aria-hidden />
            预女猎守 · 标准十人局
          </p>
          <h1 className="text-display mb-3 text-3xl leading-tight sm:text-4xl">进入议事厅</h1>
          <p className="mb-6 text-[0.9375rem] font-light leading-relaxed text-muted">
            一局十人狼杀，你与众 AI 同桌议事。开局即连实时对局，在三列棋盘上掌握局势、发言与投票。
          </p>

          <div className="space-y-4">
            <Input
              label="你的昵称"
              placeholder="输入昵称"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !loading && handleCreate()}
              error={error ?? undefined}
              autoComplete="nickname"
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <SelectField
                label="本局人格库"
                value={personalityLibId}
                onChange={(e) => setPersonalityLibId(e.target.value)}
                options={personalityOptions.length ? personalityOptions : [{ value: 'default', label: '基础库' }]}
              />
              <SelectField
                label="本局策略库"
                value={strategyLibId}
                onChange={(e) => setStrategyLibId(e.target.value)}
                options={strategyOptions.length ? strategyOptions : [{ value: 'default', label: '基础库' }]}
              />
            </div>

            <Button size="lg" className="w-full" onClick={handleCreate} disabled={loading} aria-busy={loading}>
              {loading ? '正在召唤对局…' : '开始新局'}
            </Button>

            <p className="text-center text-xs text-dim">
              {backendOk === false
                ? '后端未连接：请运行 docker compose up werewolf-backend 或本地 uvicorn :8000'
                : backendOk === true
                  ? llmOk === false
                    ? `AI 大模型未连通（将使用预设发言）：${llmError ?? '请检查 COZE_INTEGRATION_API_KEY'}`
                    : llmOk === true
                      ? '后端与 AI 大模型已就绪 · 创建后自动建立 WebSocket'
                      : '后端已就绪 · 创建后自动建立 WebSocket'
                  : '正在检测后端…'}
            </p>
          </div>
        </section>

        <section className="lobby-section lobby-divider">
          <p className="text-eyebrow mb-3">资料库管理</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Link
              to="/libraries/personalities"
              className="focus-ring lobby-link-btn group flex items-center gap-3 border border-subtle px-4 py-3 transition-colors hover:border-[var(--border-active)]"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center border border-subtle bg-[var(--bg-accent-wash)] text-warm">
                <Brain className="h-5 w-5" aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm text-mist group-hover:text-highlight">人格库</span>
                <span className="block text-xs text-dim">编辑 AI 性格与决策倾向</span>
              </span>
              <ChevronDown className="h-4 w-4 -rotate-90 text-dim" aria-hidden />
            </Link>
            <Link
              to="/libraries/strategies"
              className="focus-ring lobby-link-btn group flex items-center gap-3 border border-subtle px-4 py-3 transition-colors hover:border-[var(--border-active)]"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center border border-subtle bg-[var(--bg-accent-wash)] text-warm">
                <BookOpen className="h-5 w-5" aria-hidden />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-sm text-mist group-hover:text-highlight">策略库</span>
                <span className="block text-xs text-dim">按身份配置策略与权重</span>
              </span>
              <ChevronDown className="h-4 w-4 -rotate-90 text-dim" aria-hidden />
            </Link>
          </div>
        </section>

        <section className="lobby-section lobby-divider pb-0">
          <Collapse title="规则简述（预女猎守）">
            <ul className="list-inside list-disc space-y-2 text-sm font-light leading-relaxed text-muted">
              <li>狼人阵营 3 狼 vs 好人阵营（预言家、女巫、猎人、守卫、4 村民）。</li>
              <li>夜晚：狼刀、预言家验人、女巫用药、守卫守护，依次结算。</li>
              <li>白天：公布死讯、发言、投票放逐；猎人出局可开枪。</li>
              <li>好人屠边或狼人屠边/屠城即胜负判定。</li>
            </ul>
          </Collapse>
        </section>
      </div>
    </div>
  )
}
