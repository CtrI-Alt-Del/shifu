import type { InputHTMLAttributes } from 'react'

export type InputProps = InputHTMLAttributes<HTMLInputElement>

export const Input = ({ className = '', ...props }: InputProps) => {
  return (
    <input
      className={`min-h-11 w-full rounded-md border border-control-border bg-muted px-3 text-foreground placeholder:text-muted-foreground focus-visible:border-selo-text focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  )
}
