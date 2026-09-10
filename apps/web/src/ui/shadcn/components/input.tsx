import type * as React from 'react'
import { cn } from '@/ui/shadcn/utils/index'

function Input({ className, type, ...props }: React.ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot='input'
      className={cn(
        'flex h-9 w-full rounded-[2px] border border-control-border bg-surface px-3 py-1 text-sm text-text-primary placeholder:text-text-disabled transition-colors outline-none focus-visible:ring-2 focus-visible:ring-selo-text disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
