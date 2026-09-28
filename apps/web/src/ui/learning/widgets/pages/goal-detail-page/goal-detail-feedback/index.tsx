import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'

export type GoalDetailFeedbackProps =
  | { state: 'loading' }
  | { state: 'empty'; goalId: string }
  | { state: 'not-found' }
  | { state: 'error'; isRetrying: boolean; onRetry: () => void }

export const GoalDetailFeedback = (props: GoalDetailFeedbackProps) => {
  if (props.state === 'loading') {
    return (
      <output
        aria-busy='true'
        aria-label='Carregando objetivo'
        className='mx-auto block w-full max-w-7xl space-y-7 pb-6'
      >
        <div
          aria-hidden='true'
          className='flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between'
        >
          <div className='w-full max-w-4xl space-y-3'>
            <Skeleton className='h-10 w-3/5 max-w-md' />
            <Skeleton className='h-5 w-full max-w-lg' />
          </div>
          <Skeleton className='h-11 w-40 shrink-0' />
        </div>
        <div
          aria-hidden='true'
          className='flex flex-wrap items-center justify-between gap-4'
        >
          <Skeleton className='h-11 w-36' />
          <Skeleton className='h-11 w-52' />
        </div>
        <div
          aria-hidden='true'
          className='relative h-[40rem] overflow-hidden rounded-[10px] border border-border bg-surface-alt px-5'
        >
          <Skeleton className='absolute left-3 top-3 size-11' />
          <div className='mx-auto flex h-full max-w-[388px] flex-col items-center pt-28'>
            <div className='w-full rounded-[10px] border border-border bg-card p-4'>
              <Skeleton className='h-5 w-2/3' />
              <Skeleton className='mt-2 h-4 w-1/3' />
            </div>
            <div className='h-14 w-px bg-border' />
            <div className='w-full max-w-[352px] rounded-[10px] border border-border bg-card p-4'>
              <Skeleton className='h-5 w-3/4' />
              <Skeleton className='mt-5 h-2 w-full' />
              <Skeleton className='mt-3 h-4 w-1/2' />
            </div>
            <div className='h-10 w-px bg-border' />
            <div className='w-full max-w-[352px] rounded-[10px] border border-border bg-card p-4'>
              <Skeleton className='h-5 w-2/3' />
              <Skeleton className='mt-5 h-2 w-full' />
              <Skeleton className='mt-3 h-4 w-1/3' />
            </div>
          </div>
          <Skeleton className='absolute bottom-5 right-5 h-11 w-32' />
        </div>
        <span className='sr-only'>Carregando objetivo</span>
      </output>
    )
  }

  if (props.state === 'empty') {
    return (
      <section className='flex min-h-[540px] flex-col items-center justify-center rounded-[10px] border border-border bg-surface-alt p-8 text-center'>
        <span className='flex size-12 items-center justify-center rounded-full bg-muted'>
          <Icon className='text-foreground/80' name='network' size={22} />
        </span>
        <h2 className='mt-4 text-xl font-semibold'>
          Este objetivo ainda não tem habilidades
        </h2>
        <p className='mt-4 max-w-[560px] text-foreground/80'>
          Adicione uma habilidade do Currículo para começar. O diagnóstico só inicia
          quando você escolher iniciar a habilidade.
        </p>
        <Link
          className='mt-4 inline-flex min-h-11 items-center rounded-md bg-primary px-4 font-semibold text-primary-foreground'
          params={{ goalId: props.goalId }}
          to='/learning/goals/$goalId/skills/add'
        >
          Adicionar Habilidade
        </Link>
      </section>
    )
  }

  if (props.state === 'not-found') {
    return (
      <section
        aria-labelledby='goal-not-found-title'
        className='rounded-lg border border-border bg-card p-8 text-center'
      >
        <Icon className='mx-auto text-muted-foreground' name='lock-keyhole' size={32} />
        <h1
          autoFocus
          className='mt-4 font-serif text-3xl'
          id='goal-not-found-title'
          tabIndex={-1}
        >
          Objetivo não encontrado
        </h1>
        <p className='mt-3 text-muted-foreground'>
          Não foi possível encontrar este objetivo.
        </p>
        <Link
          className='mt-6 inline-flex min-h-11 items-center rounded-md border border-control-border px-4 font-semibold'
          to='/'
        >
          Voltar para a Home
        </Link>
      </section>
    )
  }

  return (
    <section
      aria-labelledby='goal-detail-error-title'
      className='rounded-lg border border-border bg-card p-8 text-center'
      role='alert'
    >
      <Icon className='mx-auto text-selo-text' name='circle-alert' size={32} />
      <h1
        autoFocus
        className='mt-4 font-serif text-3xl'
        id='goal-detail-error-title'
        tabIndex={-1}
      >
        Não foi possível carregar este objetivo
      </h1>
      <p className='mt-3 text-muted-foreground'>Tente novamente em alguns instantes.</p>
      <Button
        className='mt-6'
        disabled={props.isRetrying}
        onClick={props.onRetry}
        type='button'
      >
        Tentar novamente
      </Button>
    </section>
  )
}
