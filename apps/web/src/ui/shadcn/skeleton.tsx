import type { HTMLAttributes } from 'react'

export type SkeletonProps = HTMLAttributes<HTMLDivElement>

export const Skeleton = ({ className = '', ...props }: SkeletonProps) => (
  <div
    className={`motion-safe:animate-pulse rounded-md bg-muted ${className}`}
    data-slot='skeleton'
    {...props}
  />
)
