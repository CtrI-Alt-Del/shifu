import type * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/ui/shadcn/utils/index'

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-selo-text rounded-[2px] cursor-pointer",
  {
    variants: {
      variant: {
        default: 'bg-selo-fill text-white hover:bg-selo-fill/90 font-semibold',
        jade: 'bg-jade-solid text-on-jade hover:bg-jade-solid/90 font-semibold',
        latao: 'bg-latao-solid text-on-latao hover:bg-latao-solid/90 font-semibold',
        destructive:
          'bg-surface border border-selo-text text-selo-text hover:bg-selo-tint',
        outline:
          'border border-control-border bg-surface text-text-primary hover:bg-raised hover:text-white',
        secondary: 'bg-raised text-text-primary hover:bg-raised/80',
        ghost: 'hover:bg-raised hover:text-text-primary',
        link: 'text-selo-text underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-9 px-4 py-2 has-[>svg]:px-3',
        sm: 'h-8 px-3 text-xs has-[>svg]:px-2.5',
        lg: 'h-11 px-6 text-base has-[>svg]:px-4',
        icon: 'size-9',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button'

  return (
    <Comp
      data-slot='button'
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
