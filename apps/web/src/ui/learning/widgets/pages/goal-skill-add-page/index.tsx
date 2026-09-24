import { Link } from '@tanstack/react-router'

export type GoalSkillAddPageProps = { goalId: string }

export const GoalSkillAddPage = ({ goalId }: GoalSkillAddPageProps) => {
  return (
    <section className='rounded-lg border border-border bg-card p-8 text-center'>
      <h1 className='font-serif text-3xl'>Adicionar Habilidade</h1>
      <p className='mx-auto mt-3 max-w-xl leading-7 text-muted-foreground'>
        Escolha uma Habilidade do currículo para incluí-la neste Objetivo.
      </p>
      <p className='mx-auto mt-2 max-w-xl text-sm text-muted-foreground'>
        A seleção de Habilidades e bases sugeridas será disponibilizada neste fluxo.
      </p>
      <Link
        className='mt-6 inline-flex min-h-11 items-center rounded-md border border-control-border px-4 font-semibold'
        params={{ goalId }}
        to='/learning/goals/$goalId'
      >
        Voltar para o Objetivo
      </Link>
    </section>
  )
}
