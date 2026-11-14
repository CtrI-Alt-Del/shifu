import { forwardRef, type ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'default' | 'ghost' | 'danger' | 'outline'

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
}

const VARIANT_CLASS_NAMES: Record<ButtonVariant, string> = {
  default: 'bg-primary text-primary-foreground hover:bg-primary/90',
  ghost: 'bg-transparent text-muted-foreground hover:bg-white/5 hover:text-foreground',
  danger: 'bg-danger text-white hover:bg-danger/90',
  outline: 'border border-control-border bg-transparent text-foreground hover:bg-white/5',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className = '', variant = 'default', ...props },
  ref,
) {
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center rounded-md px-4 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANT_CLASS_NAMES[variant]} ${className}`}
      ref={ref}
      {...props}
    />
  )
})
