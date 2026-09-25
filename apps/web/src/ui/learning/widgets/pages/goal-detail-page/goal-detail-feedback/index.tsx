import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'

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
        className='block space-y-5 rounded-lg border border-border bg-card p-6'
      >
        <div aria-hidden='true' className='h-10 w-2/3 animate-pulse rounded bg-muted' />
        <div aria-hidden='true' className='h-5 w-full animate-pulse rounded bg-muted' />
        <div aria-hidden='true' className='h-64 animate-pulse rounded bg-muted' />
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
