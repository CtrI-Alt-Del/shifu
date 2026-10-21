import { Skeleton } from '@/ui/shadcn/skeleton'

export const LoadingSkeleton = () => (
  <div className='space-y-6'>
    <output className='sr-only'>Carregando conversa…</output>
    <div aria-hidden='true' className='ml-auto w-3/4 space-y-2 rounded-xl bg-muted p-4'>
      <Skeleton className='h-4 w-full bg-border!' />
      <Skeleton className='h-4 w-2/3 bg-border!' />
    </div>
    <div aria-hidden='true' className='w-5/6 space-y-3'>
      <Skeleton className='size-8 rounded-full!' />
      <Skeleton className='h-4 w-full' />
      <Skeleton className='h-4 w-full' />
      <Skeleton className='h-4 w-3/4' />
    </div>
  </div>
)
