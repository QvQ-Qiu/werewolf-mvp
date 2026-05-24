import { cn } from '../../lib/cn'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export function Input({ label, error, className, id, ...props }: InputProps) {
  const inputId = id ?? label?.replace(/\s/g, '-').toLowerCase()
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-caption">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={cn(
          'input-field focus-ring px-3 py-2 text-sm',
          error && 'border-[var(--border-active)]',
          className,
        )}
        {...props}
      />
      {error && <p className="text-xs font-light text-soft">{error}</p>}
    </div>
  )
}
