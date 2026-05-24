import { ChevronDown } from 'lucide-react'
import { cn } from '../../lib/cn'

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

interface SelectFieldProps extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string
  error?: string
  options: SelectOption[]
}

export function SelectField({ label, error, options, className, id, ...props }: SelectFieldProps) {
  const selectId = id ?? label?.replace(/\s/g, '-').toLowerCase()
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={selectId} className="text-caption">
          {label}
        </label>
      )}
      <div className="select-field-wrap">
        <select
          id={selectId}
          className={cn('select-field focus-ring', error && 'border-[var(--border-active)]', className)}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="select-field-chevron h-4 w-4" aria-hidden />
      </div>
      {error && <p className="text-xs font-light text-soft">{error}</p>}
    </div>
  )
}
