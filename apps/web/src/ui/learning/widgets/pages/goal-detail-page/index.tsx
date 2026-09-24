import { Link } from '@tanstack/react-router'

import { Button } from '@/ui/shadcn/button'

import { useGoalDetailPage } from './use-goal-detail-page'

const STATUS_LABELS = {
  'not-started': 'Não iniciada',
  diagnosing: 'Diagnóstico em andamento',
  learning: 'Em aprendizado',
  completed: 'Concluída',
} as const

export type GoalDetailPageProps = { goalId: string }

export const GoalDetailPage = ({ goalId }: GoalDetailPageProps) => {
  const { goal, isLoading, isPrivateAbsence, isRecoverableError, handleRetry } =
    useGoalDetailPage(goalId)

  if (isLoading)
    return (
      <output className='mx-auto block w-full max-w-7xl'>Carregando Objetivo...</output>
    )
  if (isPrivateAbsence)
    return (
      <h1 className='mx-auto w-full max-w-7xl font-serif text-3xl'>
        Objetivo não encontrado
      </h1>
    )
  if (isRecoverableError || !goal) {
    return (
      <section className='mx-auto w-full max-w-7xl space-y-4' role='alert'>
        <h1 className='font-serif text-3xl'>Não foi possível carregar o Objetivo</h1>
        <Button onClick={() => void handleRetry()} type='button'>
          Tentar novamente
        </Button>
      </section>
    )
  }

  return (
    <main className='mx-auto w-full max-w-7xl space-y-8 pb-10'>
      <header className='max-w-3xl'>
        <p className='text-xs font-bold uppercase tracking-[0.12em] text-primary'>
          Objetivo
        </p>
        <h1 className='mt-2 font-serif text-4xl font-semibold tracking-tight'>
          {goal.title}
        </h1>
        <p className='mt-4 leading-7 text-muted-foreground'>{goal.description}</p>
      </header>
      <section aria-labelledby='goal-skills-title'>
        <h2 className='font-serif text-2xl font-semibold' id='goal-skills-title'>
          Habilidades
        </h2>
        {goal.skills.length === 0 ? (
          <p className='mt-4 rounded-md border border-border bg-card p-6 text-muted-foreground'>
            Este Objetivo ainda não tem Habilidades.
          </p>
        ) : (
          <ul className='mt-4 grid gap-3 md:grid-cols-2'>
            {goal.skills.map((skill) => (
              <li key={skill.skillId}>
                <Link
                  className='flex min-h-28 flex-col justify-between gap-3 rounded-md border border-border bg-card p-5 hover:border-control-border hover:bg-muted'
                  params={{ goalId, skillId: skill.skillId }}
                  to='/learning/goals/$goalId/skills/$skillId'
                >
                  <span className='font-serif text-xl font-semibold'>
                    {skill.skillName}
                  </span>
                  <span className='text-sm text-muted-foreground'>
                    {STATUS_LABELS[skill.status]}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}
