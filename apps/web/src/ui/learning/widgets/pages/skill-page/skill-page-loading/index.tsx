import { Skeleton } from '@/ui/shadcn/skeleton'

export const SkillPageLoading = () => (
  <output className='mx-auto block w-full max-w-7xl pb-10'>
    <div className='mx-auto w-full space-y-8' aria-hidden='true'>
      <div className='flex items-start justify-between gap-4'>
        <div className='min-w-0 flex-1'>
          <Skeleton className='h-4 w-36' />
          <Skeleton className='mt-8 h-3 w-20' />
          <Skeleton className='mt-3 h-10 w-4/5 max-w-2xl' />
        </div>
        <Skeleton className='size-11 shrink-0' />
      </div>
      <div className='rounded-md border border-border bg-card p-6'>
        <Skeleton className='h-7 w-3/5 max-w-72' />
        <Skeleton className='mt-5 h-4 w-full' />
        <Skeleton className='mt-2 h-4 w-4/5' />
        <Skeleton className='mt-6 h-11 w-36' />
      </div>
    </div>
    <span className='sr-only'>Carregando Habilidade...</span>
  </output>
)
