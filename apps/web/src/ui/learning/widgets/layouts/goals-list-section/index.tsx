import { ObjectiveCard } from '@/ui/learning/widgets/components/objective-card'
import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useGoalsListSection } from './use-goals-list-section'

const SKELETON_CARD_KEYS = ['first', 'second', 'third'] as const

export const GoalsListSection = () => {
  const { goals, goalsCountLabel, handleRetry, state } = useGoalsListSection()

  return (
    <section aria-labelledby='goals-list-section-heading'>
      <div className='flex items-baseline justify-between gap-4'>
        <h2
          className='font-serif text-2xl tracking-tight sm:text-3xl'
          id='goals-list-section-heading'
        >
          Seus Objetivos
        </h2>
        {state === 'populated' && (
          <span className='text-sm text-muted-foreground'>{goalsCountLabel}</span>
        )}
        {state === 'loading' && <Skeleton aria-hidden='true' className='h-4 w-20' />}
      </div>

      {state === 'loading' && (
        <output className='mt-6 block'>
          <span className='sr-only'>Carregando seus objetivos...</span>
          <div aria-hidden='true' className='grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
            {SKELETON_CARD_KEYS.map((key) => (
              <div
                className='flex min-h-50 flex-col justify-between gap-4 rounded-2xl border border-border bg-card p-6'
                key={key}
              >
                <div className='space-y-3'>
                  <Skeleton className='h-6 w-3/4' />
                  <Skeleton className='h-4 w-full' />
                  <Skeleton className='h-4 w-5/6' />
                </div>
                <div className='flex items-center justify-between'>
                  <Skeleton className='h-4 w-24' />
                  <Skeleton className='h-5 w-5' />
                </div>
              </div>
            ))}
          </div>
        </output>
      )}

      {state === 'error' && (
        <div className='mt-6 flex flex-col items-start gap-3 rounded-2xl border border-dashed border-border p-6'>
          <p className='flex items-center gap-2 text-sm text-foreground' role='alert'>
            <Icon name='circle-alert' size={16} />
            Não foi possível carregar seus objetivos agora.
          </p>
          <Button onClick={handleRetry} type='button'>
            Tentar novamente
          </Button>
        </div>
      )}

      {state === 'empty' && (
        <div className='mt-6 rounded-2xl border border-dashed border-border p-7'>
          <p className='font-serif text-xl'>Você ainda não tem objetivos.</p>
          <p className='mt-2 max-w-xl text-sm leading-6 text-muted-foreground'>
            Crie manualmente ou descreva sua intenção acima para começar.
          </p>
        </div>
      )}

      {state === 'populated' && (
        <div className='home-page__goals mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3'>
          {goals.map((goal) => (
            <ObjectiveCard
              description={goal.description}
              id={goal.id}
              key={goal.id}
              skillCount={goal.skillCount}
              title={goal.title}
            />
          ))}
        </div>
      )}
    </section>
  )
}
