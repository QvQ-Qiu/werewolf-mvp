import { Link } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '../ui/Button'

export function LoadingState({ message = '加载中…' }: { message?: string }) {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 text-muted" role="status">
      <Loader2 className="h-8 w-8 animate-spin text-warm" aria-hidden />
      <p>{message}</p>
    </div>
  )
}

export function ErrorState({
  title = '出了点问题',
  message,
  backTo = '/',
  backLabel = '返回大厅',
}: {
  title?: string
  message: string
  backTo?: string
  backLabel?: string
}) {
  return (
    <div className="panel-surface mx-auto max-w-md p-8 text-center">
      <AlertCircle className="mx-auto mb-4 h-10 w-10 text-alert" aria-hidden />
      <h1 className="text-display mb-2 text-xl text-mist">{title}</h1>
      <p className="mb-6 text-sm text-muted">{message}</p>
      <Link to={backTo}>
        <Button variant="secondary">{backLabel}</Button>
      </Link>
    </div>
  )
}

export function NotFoundPage() {
  return (
    <ErrorState
      title="页面不存在"
      message="你访问的路径不在议事厅内，请返回大厅重新开始。"
    />
  )
}
