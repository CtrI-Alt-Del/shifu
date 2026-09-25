import { Link } from '@tanstack/react-router'

import { Button } from '@/ui/shadcn/button'

import { type MaterialPageProps, useMaterialPage } from './use-material-page'

export type { MaterialPageProps } from './use-material-page'

export const MaterialPage = (props: MaterialPageProps) => {
  const { detail, isLoading, isPrivateAbsence, isRecoverableError, handleRetry } =
    useMaterialPage(props)

  if (isLoading) {
    return (
      <output
        aria-label='Carregando Material de apoio...'
        className='mx-auto block w-full max-w-7xl'
      >
        Carregando Material de apoio...
      </output>
    )
  }
  if (isPrivateAbsence) {
    return (
      <h1 className='mx-auto w-full max-w-7xl font-serif text-3xl'>
        Material não encontrado
      </h1>
    )
  }
  if (isRecoverableError || !detail) {
    return (
      <section className='mx-auto w-full max-w-7xl space-y-4' role='alert'>
        <h1 className='font-serif text-3xl'>Não foi possível carregar o Material</h1>
        <Button onClick={() => void handleRetry()} type='button'>
          Tentar novamente
        </Button>
      </section>
    )
  }

  return (
    <div className='mx-auto w-full max-w-7xl'>
      <article className='mx-auto w-full max-w-[68ch] pb-10'>
        <Link
          className='inline-flex min-h-11 items-center text-sm font-semibold text-muted-foreground hover:text-foreground'
          params={{
            goalId: props.goalId,
            skillId: props.skillId,
            competencyId: props.competencyId,
          }}
          to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
        >
          Voltar para a Competência
        </Link>
        <header className='mt-6 border-b border-border pb-6'>
          <p className='text-xs font-bold uppercase tracking-[0.12em] text-primary'>
            Material de apoio
          </p>
          <h1 className='mt-2 font-serif text-4xl font-semibold tracking-tight'>
            {detail.title}
          </h1>
        </header>
        <div className='mt-7 whitespace-pre-wrap text-base leading-7 text-foreground'>
          {detail.content}
        </div>
        <p className='mt-8 text-sm text-muted-foreground'>
          A leitura é opcional e não altera seu progresso. Você pode praticar a qualquer
          momento.
        </p>
      </article>
    </div>
  )
}
