import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'

type FeedbackRouteProps = {
  competencyId: string
  goalId: string
  skillId: string
}

export type MaterialFeedbackProps =
  | { state: 'loading' }
  | { state: 'private-absence' }
  | (FeedbackRouteProps & {
      state: 'unavailable'
      competencyName: string
      focusCompetencyId: string | null
      focusCompetencyName: string | null
    })
  | {
      state: 'error'
      onRetry: () => void
    }

export const MaterialFeedback = (props: MaterialFeedbackProps) => {
  if (props.state === 'loading') {
    return (
      <div className='flex min-h-[calc(100dvh-10rem)] w-full flex-1 items-center justify-center'>
        <output
          aria-label='Carregando o material de apoio...'
          aria-live='polite'
          className='flex w-full max-w-[68ch] flex-col gap-5 rounded-2xl border border-border bg-card p-8 sm:p-10'
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
            className='h-24 w-full animate-pulse rounded-md bg-muted'
          />
          <div
            aria-hidden='true'
            className='h-24 w-full animate-pulse rounded-md bg-muted'
          />
          <p>Carregando o material de apoio...</p>
        </output>
      </div>
    )
  }

  if (props.state === 'private-absence') {
    return (
      <div className='flex min-h-[calc(100dvh-10rem)] w-full flex-1 items-center justify-center'>
        <output
          aria-labelledby='material-not-found-title'
          className='flex w-full max-w-3xl flex-col items-center rounded-2xl border border-border bg-card p-8 text-center sm:p-10'
        >
          <div className='mb-5 grid size-12 place-items-center rounded-md bg-muted text-muted-foreground'>
            <Icon name='lock-keyhole' size={22} />
          </div>
          <h1
            autoFocus
            className='font-serif text-3xl font-bold tracking-tight sm:text-4xl'
            id='material-not-found-title'
            tabIndex={-1}
          >
            Recurso não encontrado
          </h1>
          <p className='mt-4 max-w-xl text-muted-foreground'>
            Não foi possível encontrar este Material de apoio.
          </p>
        </output>
      </div>
    )
  }

  if (props.state === 'unavailable') {
    return (
      <div className='flex min-h-[calc(100dvh-10rem)] w-full flex-1 items-center justify-center'>
        <output
          aria-labelledby='material-unavailable-title'
          className='flex w-full max-w-3xl flex-col items-center rounded-2xl border border-border bg-card p-8 text-center sm:p-10'
        >
          <div className='mb-5 grid size-12 place-items-center rounded-md bg-muted text-muted-foreground'>
            <Icon name='lock-keyhole' size={22} />
          </div>
          <h1
            className='font-serif text-3xl font-bold tracking-tight sm:text-4xl'
            id='material-unavailable-title'
          >
            Material ainda indisponível
          </h1>
          <p className='mt-4 max-w-xl text-muted-foreground'>
            {props.focusCompetencyName === null ||
            props.focusCompetencyId === props.competencyId
              ? `O conteúdo da Competência ${props.competencyName} ainda não foi liberado nesta Habilidade.`
              : `A Competência ${props.competencyName} ainda não foi liberada. Avance em ${props.focusCompetencyName} para abrir o conteúdo dela.`}
          </p>
          <Link
            className='mt-6 inline-flex min-h-11 items-center justify-center rounded-md border border-control-border px-4 font-semibold text-foreground transition-colors hover:bg-muted'
            params={{
              competencyId: props.competencyId,
              goalId: props.goalId,
              skillId: props.skillId,
            }}
            to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
          >
            Voltar para a Competência
          </Link>
        </output>
      </div>
    )
  }

  return (
    <div className='flex min-h-[calc(100dvh-10rem)] w-full flex-1 items-center justify-center'>
      <section
        aria-labelledby='material-error-title'
        className='flex w-full max-w-3xl flex-col items-center rounded-2xl border border-border bg-card p-8 text-center sm:p-10'
        role='alert'
      >
        <div className='mb-5 grid size-12 place-items-center rounded-md bg-accent text-selo-text'>
          <Icon name='circle-alert' size={22} />
        </div>
        <h1
          autoFocus
          className='font-serif text-3xl font-bold tracking-tight sm:text-4xl'
          id='material-error-title'
          tabIndex={-1}
        >
          Não foi possível carregar este Material
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
