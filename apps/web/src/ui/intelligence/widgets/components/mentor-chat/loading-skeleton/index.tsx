import { Skeleton } from '@/ui/shadcn/skeleton'

export type LoadingSkeletonProps = { surface: 'page' | 'fab' }

export const LoadingSkeleton = ({ surface }: LoadingSkeletonProps) => (
  <div className='flex min-h-0 flex-1 gap-5'>
    <output className='sr-only'>Confirmando sua sessão…</output>
    {surface === 'page' ? (
      <div
        aria-hidden='true'
        className='hidden w-[300px] shrink-0 space-y-3 rounded-xl border border-border bg-surface-alt p-3 sm:block'
      >
        <Skeleton className='h-8 w-28' />
        <Skeleton className='h-11 w-full' />
        <Skeleton className='h-11 w-full' />
        <Skeleton className='h-16 w-full' />
        <Skeleton className='h-16 w-full' />
        <Skeleton className='h-16 w-full' />
      </div>
    ) : null}
    <div aria-hidden='true' className='flex min-w-0 flex-1 flex-col gap-6 p-4'>
      <div className='flex flex-wrap items-center justify-between gap-4'>
        <Skeleton className='h-9 w-48 max-w-full' />
        <Skeleton className='h-8 w-40 max-w-full' />
      </div>
      <div className='flex flex-1 flex-col items-center justify-center gap-4'>
        <Skeleton className='size-14 rounded-full!' />
        <Skeleton className='h-8 w-52 max-w-full' />
        <Skeleton className='h-4 w-72 max-w-full' />
      </div>
      <Skeleton className='h-14 w-full' />
    </div>
  </div>
)
