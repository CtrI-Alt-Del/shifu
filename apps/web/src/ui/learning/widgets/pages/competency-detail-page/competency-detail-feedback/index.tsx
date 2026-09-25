import { useRef } from 'react'
import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'

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
      <div className='mx-auto flex min-h-[calc(100dvh-10rem)] w-full max-w-7xl flex-1 items-center justify-center'>
        <output
          aria-live='polite'
          aria-label='Carregando Competência e seu progresso...'
          className='flex w-full max-w-3xl flex-col gap-5 rounded-2xl border border-border bg-card p-8 sm:p-10'
        >
          <div
            aria-hidden='true'
            className='h-7 w-2/3 animate-pulse rounded-md bg-muted'
          />
          <div
            aria-hidden='true'
            className='h-5 w-1/2 animate-pulse rounded-md bg-muted'
          />
          <div
            aria-hidden='true'
            className='h-14 w-full animate-pulse rounded-md bg-muted'
          />
          <div
            aria-hidden='true'
            className='h-14 w-full animate-pulse rounded-md bg-muted'
          />
          <div
            aria-hidden='true'
            className='h-14 w-full animate-pulse rounded-md bg-muted'
          />
          <p>Carregando Competência e seu progresso...</p>
        </output>
      </div>
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
