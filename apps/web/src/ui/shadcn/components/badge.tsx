import type * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/ui/shadcn/utils/index'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-mono font-medium rounded-[2px] border transition-colors',
  {
    variants: {
      variant: {
        default: 'border-divider bg-raised text-text-secondary',
        jade: 'border-jade-fill/40 bg-jade-tint text-jade-text',
        selo: 'border-selo-fill/40 bg-selo-tint text-selo-text',
        latao: 'border-latao-fill/40 bg-latao-tint text-latao-text',
        outline: 'border-control-border text-text-muted bg-transparent',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
