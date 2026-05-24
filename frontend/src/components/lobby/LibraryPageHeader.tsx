import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'

interface LibraryPageHeaderProps {
  title: string
  subtitle: string
  backTo?: string
  backLabel?: string
}

export function LibraryPageHeader({
  title,
  subtitle,
  backTo = '/',
  backLabel = '返回议事厅',
}: LibraryPageHeaderProps) {
  return (
    <div className="mb-6">
      <Link
        to={backTo}
        className="focus-ring mb-4 inline-flex items-center gap-1.5 text-sm font-light text-muted transition-colors hover:text-mist"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden />
        {backLabel}
      </Link>
      <p className="text-eyebrow mb-1">{subtitle}</p>
      <h1 className="text-display text-2xl sm:text-3xl">{title}</h1>
    </div>
  )
}
