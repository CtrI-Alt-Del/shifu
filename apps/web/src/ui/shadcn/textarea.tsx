import type { ComponentProps } from 'react'

export type TextareaProps = ComponentProps<'textarea'>

export const Textarea = ({ className = '', ...props }: TextareaProps) => {
  return (
    <textarea
      className={`w-full rounded-md border border-control-border bg-muted px-3 py-3 text-foreground placeholder:text-muted-foreground focus-visible:border-selo-text focus-visible:ring-2 focus-visible:ring-accent focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  )
}
