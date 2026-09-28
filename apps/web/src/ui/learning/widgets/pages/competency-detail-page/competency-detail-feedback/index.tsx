import { useRef } from 'react'
import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'

type FeedbackRouteProps = {
  goalId: string
  skillId: string
}

export type CompetencyDetailFeedbackProps =
  | { state: 'loading' }
  | { state: 'private-absence' }
  | (FeedbackRouteProps & {
      state: 'unavailable'
      focusCompetencyName: string | null
    })
  | {
      state: 'error'
      onRetry: () => void
    }

export const CompetencyDetailFeedback = (props: CompetencyDetailFeedbackProps) => {
  const errorTitleRef = useRef<HTMLHeadingElement>(null)

  if (props.state === 'loading') {
    return (
      <output
        aria-busy='true'
        aria-label='Carregando Competência e seu progresso...'
        className='mx-auto block w-full max-w-7xl space-y-7 pb-6 sm:space-y-9'
      >
        <div aria-hidden='true' className='space-y-5'>
          <Skeleton className='h-11 w-52' />
          <div className='flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between'>
            <div className='min-w-0 max-w-4xl flex-1'>
              <Skeleton className='mb-3 hidden h-5 w-48 lg:block' />
              <Skeleton className='h-10 w-3/4 sm:h-14' />
              <div className='mt-4 flex gap-2'>
                <Skeleton className='h-8 w-24' />
                <Skeleton className='h-8 w-32' />
              </div>
            </div>
            <div className='w-full max-w-xl lg:min-w-[22rem]'>
              <Skeleton className='h-4 w-48' />
              <Skeleton className='mt-2 h-2.5 w-full rounded-full' />
            </div>
          </div>
          <div className='flex items-start gap-3 rounded-md border border-border bg-card px-3 py-3'>
            <Skeleton className='mt-0.5 size-5 shrink-0' />
            <div className='flex-1 space-y-2'>
              <Skeleton className='h-4 w-full' />
              <Skeleton className='h-4 w-2/3' />
            </div>
          </div>
        </div>

        <section
          aria-hidden='true'
          className='rounded-md border border-control-border bg-card p-5 sm:p-6'
        >
          <Skeleton className='h-3 w-40' />
          <Skeleton className='mt-3 h-8 w-2/3 max-w-md' />
          <Skeleton className='mt-3 h-4 w-5/6' />
          <div className='mt-5 flex flex-col gap-3 sm:flex-row'>
            <Skeleton className='h-11 w-full sm:w-48' />
            <Skeleton className='h-11 w-full sm:w-64' />
          </div>
        </section>

        <ol aria-hidden='true' className='relative space-y-3'>
          {['first', 'second', 'third'].map((key) => (
            <li className='flex gap-4 lg:gap-5' key={key}>
              <Skeleton className='size-11 shrink-0 rounded-full lg:size-12' />
              <div className='flex min-h-16 min-w-0 flex-1 items-center justify-between gap-4 rounded-md border border-border bg-card px-4 py-3 lg:min-h-[68px] lg:px-5'>
                <div className='min-w-0 flex-1 space-y-2'>
                  <Skeleton className='h-5 w-3/4' />
                  <Skeleton className='h-4 w-40' />
                </div>
                <Skeleton className='size-5 shrink-0' />
              </div>
            </li>
          ))}
        </ol>
        <span className='sr-only'>Carregando Competência e seu progresso...</span>
      </output>
    )
  }

  if (props.state === 'private-absence') {
    return (
      <div className='mx-auto flex min-h-[calc(100dvh-10rem)] w-full max-w-7xl flex-1 items-center justify-center'>
        <output
          aria-labelledby='competency-detail-not-found-title'
          className='flex w-full max-w-3xl flex-col items-center rounded-2xl border border-border bg-card p-8 text-center sm:p-10'
        >
          <div className='mb-5 grid size-12 place-items-center rounded-md bg-muted text-muted-foreground'>
            <Icon name='lock-keyhole' size={22} />
          </div>
          <h1
            autoFocus
            className='font-serif text-3xl font-bold tracking-tight sm:text-4xl'
            id='competency-detail-not-found-title'
            tabIndex={-1}
          >
            Recurso não encontrado
          </h1>
          <p className='mt-4 max-w-xl text-muted-foreground'>
            Não foi possível encontrar esta Competência.
          </p>
        </output>
      </div>
    )
  }

  if (props.state === 'unavailable') {
    return (
      <div className='mx-auto flex min-h-[calc(100dvh-10rem)] w-full max-w-7xl flex-1 items-center justify-center'>
        <output
          aria-labelledby='competency-detail-unavailable-title'
          className='flex w-full max-w-3xl flex-col items-center rounded-2xl border border-border bg-card p-8 text-center sm:p-10'
        >
          <div className='mb-5 grid size-12 place-items-center rounded-md bg-muted text-muted-foreground'>
            <Icon name='lock-keyhole' size={22} />
          </div>
          <h1
            className='font-serif text-3xl font-bold tracking-tight sm:text-4xl'
            id='competency-detail-unavailable-title'
          >
            Competência ainda indisponível
          </h1>
          <p className='mt-4 max-w-xl text-muted-foreground'>
            Avance em {props.focusCompetencyName ?? 'sua Competência em foco'} para
            liberar materiais e Atividades desta Competência.
          </p>
          <Link
            className='mt-6 inline-flex min-h-11 items-center justify-center rounded-md border border-control-border px-4 font-semibold text-foreground transition-colors hover:bg-muted'
            params={{ goalId: props.goalId, skillId: props.skillId }}
            to='/learning/goals/$goalId/skills/$skillId'
          >
            Voltar para a Habilidade
          </Link>
        </output>
      </div>
    )
  }

  return (
    <div className='mx-auto flex min-h-[calc(100dvh-10rem)] w-full max-w-7xl flex-1 items-center justify-center'>
      <section
        aria-labelledby='competency-detail-error-title'
        className='flex w-full max-w-3xl flex-col items-center rounded-2xl border border-border bg-card p-8 text-center sm:p-10'
        role='alert'
      >
        <div className='mb-5 grid size-12 place-items-center rounded-md bg-accent text-selo-text'>
          <Icon name='circle-alert' size={22} />
        </div>
        <h1
          autoFocus
          className='font-serif text-3xl font-bold tracking-tight sm:text-4xl'
          id='competency-detail-error-title'
          ref={errorTitleRef}
          tabIndex={-1}
        >
          Não foi possível carregar esta Competência
        </h1>
        <p className='mt-4 max-w-xl text-muted-foreground'>
          Seu progresso continua salvo. Tente carregar a página novamente.
        </p>
        <Button className='mt-6' onClick={props.onRetry} type='button'>
          Tentar novamente
        </Button>
      </section>
    </div>
  )
}
