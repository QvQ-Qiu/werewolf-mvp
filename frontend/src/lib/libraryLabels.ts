import type { LibraryListItem } from '../types/libraries'

export const BUILTIN_LIBRARY_ID = 'default'
export const BUILTIN_LIBRARY_LABEL = '基础库'

export function libraryOptionLabel(item: Pick<LibraryListItem, 'id' | 'name' | 'is_builtin'>): string {
  if (item.id === BUILTIN_LIBRARY_ID || item.is_builtin) return BUILTIN_LIBRARY_LABEL
  return item.name
}

export function isBuiltinLibraryId(id: string): boolean {
  return id === BUILTIN_LIBRARY_ID
}
