import type { ComponentProps } from 'react'

export type InputProps = ComponentProps<'input'>

export const Input = ({ className = '', ...props }: InputProps) => {
  return (
    <input
      className={`min-h-11 w-full rounded-md border border-control-border bg-muted px-3 text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/20 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  )
}
