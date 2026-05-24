import type { ReactNode } from 'react'
import { Button } from '../ui/Button'

export function LibraryOverlayModal({
  title,
  children,
  onClose,
  actions,
  ariaLabelledBy,
}: {
  title: string
  children: ReactNode
  onClose: () => void
  actions: ReactNode
  ariaLabelledBy?: string
}) {
  const titleId = ariaLabelledBy ?? 'library-modal-title'
  return (
    <div
      className="cinematic-layer cinematic-layer--modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="cinematic-modal panel-surface max-h-[90vh] w-full max-w-md overflow-y-auto p-5">
        <h2 id={titleId} className="dock-section-title mb-3 text-base text-highlight">
          {title}
        </h2>
        <div className="text-sm font-light leading-relaxed text-muted">{children}</div>
        <div className="mt-5 flex flex-wrap justify-end gap-2">{actions}</div>
      </div>
    </div>
  )
}

export function LibraryModalCancelButton({ onClick }: { onClick: () => void }) {
  return (
    <Button variant="ghost" onClick={onClick}>
      取消
    </Button>
  )
}
