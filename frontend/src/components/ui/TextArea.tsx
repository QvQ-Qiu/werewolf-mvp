import { cn } from '../../lib/cn'

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export function TextArea({ label, error, className, id, ...props }: TextAreaProps) {
  const areaId = id ?? label?.replace(/\s/g, '-').toLowerCase()
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={areaId} className="text-caption">
          {label}
        </label>
      )}
      <textarea
        id={areaId}
        className={cn(
          'input-field focus-ring resize-y px-3 py-2 text-sm leading-relaxed',
          error && 'border-[var(--border-active)]',
          className,
        )}
        {...props}
      />
      {error && <p className="text-xs font-light text-soft">{error}</p>}
    </div>
  )
}
