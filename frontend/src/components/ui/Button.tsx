import { cn } from '../../lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

const variantClass: Record<Variant, string> = {
  primary:
    'border-[var(--border-active)] bg-[var(--bg-accent-wash-strong)] text-highlight hover:bg-[rgba(196,168,130,0.11)] disabled:opacity-40',
  secondary:
    'border-[var(--border-medium)] bg-transparent text-mist hover:border-[var(--border-active)] hover:text-highlight disabled:opacity-40',
  ghost:
    'border-transparent bg-transparent text-muted hover:text-mist disabled:opacity-40',
  danger:
    'border-[var(--border-medium)] bg-transparent text-soft hover:border-[var(--border-active)] disabled:opacity-40',
}

const sizeClass: Record<Size, string> = {
  sm: 'px-2.5 py-1 text-xs',
  md: 'px-3.5 py-1.5 text-sm',
  lg: 'px-5 py-2 text-sm',
}

export function Button({
  className,
  variant = 'primary',
  size = 'md',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex items-center justify-center gap-2 border font-light transition-colors duration-150 focus-ring',
        variantClass[variant],
        sizeClass[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
}
