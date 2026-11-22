import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'

export type SkillCompletedNoticeProps = {
  goalId: string
  skillId: string
}

export const SkillCompletedNotice = ({ goalId, skillId }: SkillCompletedNoticeProps) => {
  return (
    <section
      aria-label='Habilidade concluída'
      className='flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-md border border-border bg-card p-4'
    >
      <p className='flex items-center gap-2 font-semibold text-foreground'>
        <Icon className='size-5 shrink-0 text-success' name='circle-check' />
        Habilidade concluída
      </p>
      <Link
        className='inline-flex min-h-11 items-center font-semibold text-foreground underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'
        params={{ goalId, skillId }}
        to='/learning/goals/$goalId/skills/$skillId'
      >
        Ver resumo final
      </Link>
    </section>
  )
}
