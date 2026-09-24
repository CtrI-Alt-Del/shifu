import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'

export type MaterialHeaderProps = {
  competencyId: string
  competencyName: string
  goalId: string
  materialTitle: string
  skillId: string
  skillName: string
}

export const MaterialHeader = ({
  competencyId,
  competencyName,
  goalId,
  materialTitle,
  skillId,
  skillName,
}: MaterialHeaderProps) => {
  return (
    <header className='max-w-[68ch] space-y-5'>
      <Link
        aria-label={`Voltar para a Competência ${competencyName}`}
        className='inline-flex min-h-11 items-center gap-2 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground'
        params={{ competencyId, goalId, skillId }}
        to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
      >
        <Icon name='arrow-left' size={16} />
        <span className='sm:hidden'>{competencyName}</span>
        <span className='hidden sm:inline'>Voltar para {competencyName}</span>
      </Link>

      <div className='min-w-0'>
        <p className='mb-3 text-sm text-muted-foreground'>
          {skillName} · {competencyName}
        </p>
        <h1 className='font-serif text-4xl font-bold tracking-tight text-foreground sm:text-5xl'>
          {materialTitle}
        </h1>
        <p className='mt-4 inline-flex min-h-8 items-center gap-2 rounded-md bg-muted px-3 py-1 text-xs font-bold text-muted-foreground'>
          <Icon name='book-open' size={14} />
          Material de apoio
        </p>
      </div>
    </header>
  )
}
