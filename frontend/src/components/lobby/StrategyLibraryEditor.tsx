import { useCallback, useEffect, useState } from 'react'
import {
  createStrategyLibrary,
  deleteStrategyLibrary,
  extendStrategyLibrary,
  fetchStrategyLibrary,
  listStrategyLibraries,
  updateStrategyLibrary,
} from '../../api/client'
import { BUILTIN_LIBRARY_ID, BUILTIN_LIBRARY_LABEL, libraryOptionLabel } from '../../lib/libraryLabels'
import {
  ROLE_OPTIONS,
  type LibraryListItem,
  type StrategyEntry,
  type StrategyLibrary,
} from '../../types/libraries'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { SelectField } from '../ui/SelectField'
import { Tabs } from '../ui/Tabs'
import { TextArea } from '../ui/TextArea'
import { LibraryModalCancelButton, LibraryOverlayModal } from './LibraryOverlayModal'

const emptyEntry = (role: string): StrategyEntry => ({
  id: `${role.toUpperCase().slice(0, 1)}NEW_${Date.now()}`,
  role,
  name: '新策略',
  tendency: 'default',
  priority: 3,
  weight: 1,
  prompt_hint: '按局势行动',
})

type LibraryModal =
  | { kind: 'create'; forkFrom?: string }
  | { kind: 'delete'; id: string; name: string }
  | { kind: 'rename' }
  | { kind: 'baseReadOnly' }
  | { kind: 'deleteEntry'; id: string; name: string }

function createDefaultName(forkFrom?: string, selectedId?: string): string {
  if (forkFrom === BUILTIN_LIBRARY_ID) return '我的策略库'
  if (forkFrom && forkFrom === selectedId) return '延续策略库'
  if (forkFrom) return '延续策略库'
  return '新策略库'
}

export function StrategyLibraryEditor() {
  const [items, setItems] = useState<LibraryListItem[]>([])
  const [selectedId, setSelectedId] = useState(BUILTIN_LIBRARY_ID)
  const [library, setLibrary] = useState<StrategyLibrary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [libraryModal, setLibraryModal] = useState<LibraryModal | null>(null)
  const [modalName, setModalName] = useState('')
  const [role, setRole] = useState<string>('wolf')
  const [editEntry, setEditEntry] = useState<StrategyEntry | null>(null)
  const [isNewEntry, setIsNewEntry] = useState(false)
  const [saving, setSaving] = useState(false)

  const readOnly = library?.is_builtin ?? false
  const roleEntries = library?.strategies_by_role[role] ?? []

  const refreshList = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const list = await listStrategyLibraries()
      setItems(list)
      if (!list.some((x) => x.id === selectedId) && list[0]) {
        setSelectedId(list[0].id)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载策略库列表失败')
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
        const lib = await fetchStrategyLibrary(selectedId)
        setLibrary(lib)
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载策略库详情失败')
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
      const lib = await createStrategyLibrary({
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
      await deleteStrategyLibrary(modal.id)
      setLibraryModal(null)
      if (selectedId === modal.id) setSelectedId(BUILTIN_LIBRARY_ID)
      setLibrary(null)
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
      const saved = await updateStrategyLibrary(library.id, {
        name,
        strategies_by_role: library.strategies_by_role,
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

  async function saveLibrary(next: StrategyLibrary) {
    if (next.is_builtin) return
    try {
      const saved = await updateStrategyLibrary(next.id, {
        name: next.name,
        strategies_by_role: next.strategies_by_role,
      })
      setLibrary(saved)
      await refreshList()
    } catch (e) {
      setError(e instanceof Error ? e.message : '保存失败')
    }
  }

  async function handleExtend() {
    if (readOnly) {
      setLibraryModal({ kind: 'baseReadOnly' })
      return
    }
    if (!selectedId || !library) return
    try {
      const lib = await extendStrategyLibrary(selectedId, {
        append_by_role: { [role]: [emptyEntry(role)] },
      })
      setLibrary(lib)
      await refreshList()
      const roleList = lib.strategies_by_role[role]
      const added = roleList?.[roleList.length - 1]
      if (added) {
        setEditEntry({ ...added })
        setIsNewEntry(true)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '延续失败')
    }
  }

  function openAddEntry() {
    guardWritable(() => {
      setEditEntry(emptyEntry(role))
      setIsNewEntry(true)
    })
  }

  function applyEntryEdit() {
    if (!editEntry || !library || readOnly) return
    const next = {
      ...library,
      strategies_by_role: {
        ...library.strategies_by_role,
        [role]: (() => {
          const list = [...(library.strategies_by_role[role] ?? [])]
          const idx = list.findIndex((e) => e.id === editEntry.id)
          if (idx >= 0) list[idx] = editEntry
          else list.push(editEntry)
          return list
        })(),
      },
    }
    void saveLibrary(next)
    setEditEntry(null)
  }

  function requestDeleteEntry(id: string, name: string) {
    guardWritable(() => setLibraryModal({ kind: 'deleteEntry', id, name }))
  }

  async function confirmDeleteEntry() {
    const modal = libraryModal
    if (modal?.kind !== 'deleteEntry' || !library) return
    setLibraryModal(null)
    const list = (library.strategies_by_role[role] ?? []).filter((e) => e.id !== modal.id)
    void saveLibrary({
      ...library,
      strategies_by_role: { ...library.strategies_by_role, [role]: list },
    })
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
          label="当前策略库"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          options={libOptions}
          disabled={loading || libOptions.length === 0}
        />

        <p className="mt-2 text-xs text-dim">
          {readOnly
            ? `${BUILTIN_LIBRARY_LABEL}为只读模板，可复制后编辑自定义策略。`
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
        <div className="mb-4">
          <h2 className="text-eyebrow mb-1">按身份管理策略</h2>
          <p className="text-xs font-light text-muted">
            {readOnly ? '仅可查看；添加或修改请新建自定义库' : '为各身份配置策略权重与提示词'}
          </p>
        </div>

        <Tabs
          items={ROLE_OPTIONS.map((r) => ({ id: r.value, label: r.label }))}
          activeId={role}
          onChange={setRole}
          className="mb-4"
        />

        <div className="mb-4 flex flex-wrap gap-2">
          <Button size="sm" onClick={openAddEntry}>
            添加策略
          </Button>
          <Button size="sm" variant="secondary" onClick={() => void handleExtend()}>
            延续追加
          </Button>
        </div>

        {loading ? (
          <p className="text-xs text-dim">加载中…</p>
        ) : (
          <ul className="space-y-2">
            {roleEntries.map((entry) => (
              <li
                key={entry.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-sm border border-subtle px-3 py-2.5"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-mist">
                    <span className="font-mono text-xs text-dim">{entry.id}</span>
                    <span className="mx-2 text-dim">·</span>
                    {entry.name}
                  </p>
                  <p className="mt-0.5 line-clamp-2 text-xs text-muted">{entry.prompt_hint}</p>
                  <p className="mt-1 text-xs text-dim">权重 {entry.weight}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setEditEntry({ ...entry })
                      setIsNewEntry(false)
                    }}
                  >
                    {readOnly ? '查看' : '编辑'}
                  </Button>
                  {!readOnly && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => requestDeleteEntry(entry.id, entry.name)}
                    >
                      删除
                    </Button>
                  )}
                </div>
              </li>
            ))}
            {roleEntries.length === 0 && (
              <p className="text-xs text-dim">该身份暂无策略条目</p>
            )}
          </ul>
        )}
      </section>

      {libraryModal?.kind === 'create' && (
        <LibraryOverlayModal
          title="新建策略库"
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
              ? '将复制基础库中的全部策略作为起点。'
              : libraryModal.forkFrom
                ? `将复制「${items.find((x) => x.id === libraryModal.forkFrom)?.name ?? libraryModal.forkFrom}」中的条目。`
                : '创建新策略库（从基础库复制内容）。'}
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
          title="删除策略库"
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
            确定删除「{libraryModal.name}」？库内所有策略条目将一并移除，此操作不可恢复。
          </p>
        </LibraryOverlayModal>
      )}

      {libraryModal?.kind === 'rename' && library && (
        <LibraryOverlayModal
          title="重命名策略库"
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

      {libraryModal?.kind === 'deleteEntry' && (
        <LibraryOverlayModal
          title="删除策略"
          onClose={() => setLibraryModal(null)}
          actions={
            <>
              <LibraryModalCancelButton onClick={() => setLibraryModal(null)} />
              <Button variant="secondary" onClick={() => void confirmDeleteEntry()}>
                确认删除
              </Button>
            </>
          }
        >
          <p>确定删除策略「{libraryModal.name}」？</p>
        </LibraryOverlayModal>
      )}

      {editEntry && (
        <div
          className="cinematic-layer cinematic-layer--modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="strategy-edit-title"
          onClick={(e) => {
            if (e.target === e.currentTarget) setEditEntry(null)
          }}
        >
          <div className="cinematic-modal panel-surface w-full max-w-md p-5">
            <h3 id="strategy-edit-title" className="dock-section-title mb-4 text-base text-highlight">
              {readOnly ? '查看策略' : isNewEntry ? '添加策略' : '编辑策略'}
            </h3>
            <div className="space-y-3">
              <Input
                label="策略 ID"
                value={editEntry.id}
                onChange={(e) => setEditEntry({ ...editEntry, id: e.target.value })}
                readOnly={readOnly || !isNewEntry}
              />
              <Input
                label="名称"
                value={editEntry.name}
                onChange={(e) => setEditEntry({ ...editEntry, name: e.target.value })}
                readOnly={readOnly}
              />
              <Input
                label="权重"
                type="number"
                min={0}
                step={0.1}
                value={editEntry.weight}
                onChange={(e) =>
                  setEditEntry({ ...editEntry, weight: Number(e.target.value) || 0 })
                }
                readOnly={readOnly}
              />
              <TextArea
                label="提示词 hint"
                value={editEntry.prompt_hint}
                onChange={(e) => setEditEntry({ ...editEntry, prompt_hint: e.target.value })}
                rows={4}
                readOnly={readOnly}
                placeholder="描述该策略下的行动倾向，供 AI 参考"
              />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setEditEntry(null)}>
                关闭
              </Button>
              {!readOnly && (
                <Button onClick={applyEntryEdit}>{isNewEntry ? '添加' : '保存'}</Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
