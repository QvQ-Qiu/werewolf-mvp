import { useCallback, useEffect, useState } from 'react'
import {
  createPersonalityLibrary,
  deletePersonalityLibrary,
  fetchPersonalityLibrary,
  listPersonalityLibraries,
  updatePersonalityLibrary,
} from '../../api/client'
import { BUILTIN_LIBRARY_ID, BUILTIN_LIBRARY_LABEL, libraryOptionLabel } from '../../lib/libraryLabels'
import type { LibraryListItem, PersonalityLibrary, PersonalityTemplate } from '../../types/libraries'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { SelectField } from '../ui/SelectField'
import { TextArea } from '../ui/TextArea'
import { LibraryModalCancelButton, LibraryOverlayModal } from './LibraryOverlayModal'

const SPEECH_LENGTH_OPTIONS = [
  { value: 'short', label: '简短' },
  { value: 'medium', label: '适中' },
  { value: 'long', label: '冗长' },
]

const DECISION_BIAS_OPTIONS = [
  { value: 'push_vote', label: '冲票归票' },
  { value: 'follow_majority', label: '跟大票' },
  { value: 'analyze_votes', label: '盘票型' },
  { value: 'stir_conflict', label: '煽动对立' },
  { value: 'fake_claim', label: '悍跳假神' },
  { value: 'minimal_talk', label: '惜字如金' },
  { value: 'emotional_vote', label: '情绪投票' },
  { value: 'default', label: '默认' },
]

type LibraryModal =
  | { kind: 'create'; forkFrom?: string }
  | { kind: 'delete'; id: string; name: string }
  | { kind: 'rename' }
  | { kind: 'baseReadOnly' }
  | { kind: 'deletePersona'; id: string; name: string }

function emptyPersona(): PersonalityTemplate {
  return {
    id: `persona_${Date.now()}`,
    name: '新人格',
    aggression: 0.5,
    logic: 0.5,
    speech_length: 'medium',
    style_hint: '',
    decision_bias: 'default',
    low_logic: false,
  }
}

function SliderField({
  label,
  value,
  onChange,
  hint,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  hint?: string
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-caption">{label}</span>
        <span className="font-mono text-xs text-dim">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="slider-field focus-ring"
      />
      {hint && <p className="text-xs text-dim">{hint}</p>}
    </div>
  )
}

function createDefaultName(forkFrom?: string, selectedId?: string): string {
  if (forkFrom === BUILTIN_LIBRARY_ID) return '我的人格库'
  if (forkFrom && forkFrom === selectedId) return '延续人格库'
  if (forkFrom) return '延续人格库'
  return '新人格库'
}

export function PersonalityLibraryEditor() {
  const [items, setItems] = useState<LibraryListItem[]>([])
  const [selectedId, setSelectedId] = useState(BUILTIN_LIBRARY_ID)
  const [library, setLibrary] = useState<PersonalityLibrary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [libraryModal, setLibraryModal] = useState<LibraryModal | null>(null)
  const [modalName, setModalName] = useState('')
  const [editPersona, setEditPersona] = useState<PersonalityTemplate | null>(null)
  const [isNewPersona, setIsNewPersona] = useState(false)
  const [saving, setSaving] = useState(false)

  const readOnly = library?.is_builtin ?? false

  const refreshList = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await listPersonalityLibraries()
      setItems(list)
      if (!list.some((x) => x.id === selectedId) && list[0]) {
        setSelectedId(list[0].id)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载人格库列表失败')
    } finally {
      setLoading(false)
    }
  }, [selectedId])

  useEffect(() => {
    void refreshList()
  }, [refreshList])

  useEffect(() => {
    if (!selectedId) return
    void (async () => {
      try {
        const lib = await fetchPersonalityLibrary(selectedId)
        setLibrary(lib)
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载人格库详情失败')
        setLibrary(null)
      }
    })()
  }, [selectedId])

  function openCreateModal(forkFrom?: string) {
    setModalName(createDefaultName(forkFrom, selectedId))
    setLibraryModal({ kind: 'create', forkFrom })
  }

  function guardWritable(action: () => void) {
    if (readOnly) {
      setLibraryModal({ kind: 'baseReadOnly' })
      return
    }
    action()
  }

  async function handleCreateConfirm() {
    const modal = libraryModal
    if (modal?.kind !== 'create') return
    const name = modalName.trim() || createDefaultName(modal.forkFrom, selectedId)
    setSaving(true)
    setError(null)
    try {
      const lib = await createPersonalityLibrary({
        name,
        fork_from: modal.forkFrom ?? BUILTIN_LIBRARY_ID,
      })
      setLibraryModal(null)
      setSelectedId(lib.id)
      setLibrary(lib)
      await refreshList()
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteConfirm() {
    const modal = libraryModal
    if (modal?.kind !== 'delete') return
    setSaving(true)
    setError(null)
    try {
      await deletePersonalityLibrary(modal.id)
      setLibraryModal(null)
      if (selectedId === modal.id) setSelectedId(BUILTIN_LIBRARY_ID)
      await refreshList()
    } catch (e) {
      setError(e instanceof Error ? e.message : '删除失败')
    } finally {
      setSaving(false)
    }
  }

  async function handleRenameConfirm() {
    if (!library || readOnly) return
    const name = modalName.trim()
    if (!name) return
    setSaving(true)
    setError(null)
    try {
      const saved = await updatePersonalityLibrary(library.id, {
        name,
        personalities: library.personalities,
      })
      setLibrary(saved)
      setLibraryModal(null)
      await refreshList()
    } catch (e) {
      setError(e instanceof Error ? e.message : '重命名失败')
    } finally {
      setSaving(false)
    }
  }

  async function handleSaveLibrary(updated: PersonalityTemplate[]) {
    if (!library || readOnly) return
    try {
      const saved = await updatePersonalityLibrary(library.id, {
        name: library.name,
        personalities: updated,
      })
      setLibrary(saved)
      await refreshList()
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败')
    }
  }

  function openEditPersona(persona: PersonalityTemplate) {
    setEditPersona({ ...persona })
    setIsNewPersona(false)
  }

  function openAddPersona() {
    guardWritable(() => {
      setEditPersona(emptyPersona())
      setIsNewPersona(true)
    })
  }

  function applyPersonaEdit() {
    if (!editPersona || !library || readOnly) return
    const list = [...library.personalities]
    const idx = list.findIndex((p) => p.id === editPersona.id)
    if (idx >= 0) list[idx] = editPersona
    else list.push(editPersona)
    void handleSaveLibrary(list)
    setEditPersona(null)
  }

  function requestDeletePersona(id: string, name: string) {
    guardWritable(() => setLibraryModal({ kind: 'deletePersona', id, name }))
  }

  async function confirmDeletePersona() {
    const modal = libraryModal
    if (modal?.kind !== 'deletePersona' || !library) return
    setLibraryModal(null)
    void handleSaveLibrary(library.personalities.filter((p) => p.id !== modal.id))
  }

  const libOptions = items.map((item) => ({
    value: item.id,
    label: libraryOptionLabel(item),
  }))

  const displayLibraryName = library
    ? library.is_builtin
      ? BUILTIN_LIBRARY_LABEL
      : library.name
    : ''

  return (
    <div className="lobby-sheet">
      <section className="lobby-section">
        {error && <p className="mb-4 text-xs text-soft">{error}</p>}

        <SelectField
          label="当前人格库"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          options={libOptions}
          disabled={loading || libOptions.length === 0}
        />

        <p className="mt-2 text-xs text-dim">
          {readOnly
            ? `${BUILTIN_LIBRARY_LABEL}为只读模板，可复制后编辑自定义人格。`
            : `正在编辑：${displayLibraryName}`}
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button size="sm" onClick={() => openCreateModal()}>
            新建库
          </Button>
          <Button size="sm" variant="secondary" onClick={() => openCreateModal(selectedId)}>
            延续当前库
          </Button>
          <Button size="sm" variant="secondary" onClick={() => openCreateModal(BUILTIN_LIBRARY_ID)}>
            从基础库复制
          </Button>
          {!readOnly && library && (
            <>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setModalName(library.name)
                  setLibraryModal({ kind: 'rename' })
                }}
              >
                重命名
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  setLibraryModal({
                    kind: 'delete',
                    id: selectedId,
                    name: library.name,
                  })
                }
              >
                删除当前库
              </Button>
            </>
          )}
        </div>
      </section>

      <section className="lobby-section lobby-divider">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-eyebrow mb-1">人格条目</h2>
            <p className="text-xs font-light text-muted">
              {readOnly ? '仅可查看；添加或修改请新建自定义库' : '调整 AI 的攻击性、逻辑与决策倾向'}
            </p>
          </div>
          <Button size="sm" onClick={openAddPersona}>
            添加人格
          </Button>
        </div>

        {loading ? (
          <p className="text-xs text-dim">加载中…</p>
        ) : (
          <ul className="space-y-2">
            {(library?.personalities ?? []).map((persona) => (
              <li
                key={persona.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-subtle px-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-mist">
                    <span className="font-mono text-xs text-dim">{persona.id}</span>
                    <span className="mx-2 text-dim">·</span>
                    {persona.name}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-muted">{persona.style_hint || '（无风格描述）'}</p>
                  <p className="mt-1 text-xs text-dim">
                    攻击性 {persona.aggression.toFixed(2)} · 逻辑 {persona.logic.toFixed(2)} ·{' '}
                    {persona.decision_bias}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button size="sm" variant="secondary" onClick={() => openEditPersona(persona)}>
                    {readOnly ? '查看' : '编辑'}
                  </Button>
                  {!readOnly && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => requestDeletePersona(persona.id, persona.name)}
                    >
                      删除
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {libraryModal?.kind === 'create' && (
        <LibraryOverlayModal
          title="新建人格库"
          onClose={() => setLibraryModal(null)}
          actions={
            <>
              <LibraryModalCancelButton onClick={() => setLibraryModal(null)} />
              <Button onClick={() => void handleCreateConfirm()} disabled={saving}>
                {saving ? '创建中…' : '创建'}
              </Button>
            </>
          }
        >
          <p className="mb-3">
            {libraryModal.forkFrom === BUILTIN_LIBRARY_ID
              ? '将复制基础库中的全部人格作为起点。'
              : libraryModal.forkFrom
                ? `将复制「${items.find((x) => x.id === libraryModal.forkFrom)?.name ?? libraryModal.forkFrom}」中的条目。`
                : '创建空白人格库（从基础库复制内容）。'}
          </p>
          <Input
            label="库名称"
            value={modalName}
            onChange={(e) => setModalName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void handleCreateConfirm()}
            autoFocus
          />
        </LibraryOverlayModal>
      )}

      {libraryModal?.kind === 'delete' && (
        <LibraryOverlayModal
          title="删除人格库"
          onClose={() => setLibraryModal(null)}
          actions={
            <>
              <LibraryModalCancelButton onClick={() => setLibraryModal(null)} />
              <Button variant="secondary" onClick={() => void handleDeleteConfirm()} disabled={saving}>
                {saving ? '删除中…' : '确认删除'}
              </Button>
            </>
          }
        >
          <p>
            确定删除「{libraryModal.name}」？库内所有人格条目将一并移除，此操作不可恢复。
          </p>
        </LibraryOverlayModal>
      )}

      {libraryModal?.kind === 'rename' && library && (
        <LibraryOverlayModal
          title="重命名人格库"
          onClose={() => setLibraryModal(null)}
          actions={
            <>
              <LibraryModalCancelButton onClick={() => setLibraryModal(null)} />
              <Button onClick={() => void handleRenameConfirm()} disabled={saving}>
                {saving ? '保存中…' : '保存'}
              </Button>
            </>
          }
        >
          <Input
            label="库名称"
            value={modalName}
            onChange={(e) => setModalName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void handleRenameConfirm()}
            autoFocus
          />
        </LibraryOverlayModal>
      )}

      {libraryModal?.kind === 'baseReadOnly' && (
        <LibraryOverlayModal
          title="无法编辑基础库"
          onClose={() => setLibraryModal(null)}
          actions={
            <>
              <LibraryModalCancelButton onClick={() => setLibraryModal(null)} />
              <Button
                onClick={() => {
                  setLibraryModal(null)
                  openCreateModal(BUILTIN_LIBRARY_ID)
                }}
              >
                新建库
              </Button>
            </>
          }
        >
          <p>请创建新库后再添加。{BUILTIN_LIBRARY_LABEL}为只读模板，可从基础库复制内容后编辑。</p>
        </LibraryOverlayModal>
      )}

      {libraryModal?.kind === 'deletePersona' && (
        <LibraryOverlayModal
          title="删除人格"
          onClose={() => setLibraryModal(null)}
          actions={
            <>
              <LibraryModalCancelButton onClick={() => setLibraryModal(null)} />
              <Button variant="secondary" onClick={() => void confirmDeletePersona()}>
                确认删除
              </Button>
            </>
          }
        >
          <p>确定删除人格「{libraryModal.name}」？</p>
        </LibraryOverlayModal>
      )}

      {editPersona && (
        <div
          className="cinematic-layer cinematic-layer--modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="persona-edit-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setEditPersona(null)
          }}
        >
          <div className="cinematic-modal panel-surface max-h-[90vh] w-full max-w-lg overflow-y-auto p-5">
            <h3 id="persona-edit-title" className="dock-section-title mb-4 text-base text-highlight">
              {readOnly ? '查看人格' : isNewPersona ? '添加人格' : '编辑人格'}
            </h3>
            <div className="space-y-4">
              <Input
                label="标识 ID"
                value={editPersona.id}
                onChange={(e) => setEditPersona({ ...editPersona, id: e.target.value })}
                readOnly={readOnly || !isNewPersona}
              />
              <Input
                label="名称"
                value={editPersona.name}
                onChange={(e) => setEditPersona({ ...editPersona, name: e.target.value })}
                readOnly={readOnly}
              />
              <SliderField
                label="攻击性"
                value={editPersona.aggression}
                onChange={(v) => setEditPersona({ ...editPersona, aggression: v })}
                hint="越高越爱冲票、带节奏"
              />
              <SliderField
                label="逻辑性"
                value={editPersona.logic}
                onChange={(v) => setEditPersona({ ...editPersona, logic: v })}
                hint="越高越注重盘逻辑与票型"
              />
              <SelectField
                label="发言长度"
                value={editPersona.speech_length ?? 'medium'}
                onChange={(e) => setEditPersona({ ...editPersona, speech_length: e.target.value })}
                options={SPEECH_LENGTH_OPTIONS}
                disabled={readOnly}
              />
              <SelectField
                label="决策倾向"
                value={editPersona.decision_bias}
                onChange={(e) => setEditPersona({ ...editPersona, decision_bias: e.target.value })}
                options={DECISION_BIAS_OPTIONS}
                disabled={readOnly}
              />
              <TextArea
                label="风格提示"
                value={editPersona.style_hint}
                onChange={(e) => setEditPersona({ ...editPersona, style_hint: e.target.value })}
                rows={3}
                readOnly={readOnly}
                placeholder="例如：爱归票、语气强硬、敢于点人"
              />
              <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={editPersona.low_logic ?? false}
                  onChange={(e) => setEditPersona({ ...editPersona, low_logic: e.target.checked })}
                  disabled={readOnly}
                  className="accent-[var(--accent-warm)]"
                />
                低逻辑模式（发言更随意、少推理）
              </label>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setEditPersona(null)}>
                关闭
              </Button>
              {!readOnly && (
                <Button onClick={applyPersonaEdit}>{isNewPersona ? '添加' : '保存'}</Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
