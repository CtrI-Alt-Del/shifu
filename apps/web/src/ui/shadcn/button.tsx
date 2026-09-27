import { forwardRef, type ButtonHTMLAttributes } from 'react'

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'default' | 'ghost' | 'danger'
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className = '', variant = 'default', ...props },
  ref,
) {
  const variantClassName =
    variant === 'ghost'
      ? 'bg-transparent text-muted-foreground hover:bg-white/5 hover:text-foreground'
      : variant === 'danger'
        ? 'bg-danger text-white hover:bg-danger/90'
        : 'bg-primary text-primary-foreground hover:bg-primary/90'

  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center rounded-md px-4 font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${variantClassName} ${className}`}
      ref={ref}
      {...props}
    />
  )
})
