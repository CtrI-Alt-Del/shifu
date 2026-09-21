import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'

export type ObjectiveCardProps = {
  description: string
  id: string
  skillCount: number
  title: string
}

export const ObjectiveCard = ({
  description,
  id,
  skillCount,
  title,
}: ObjectiveCardProps) => {
  const skillCountLabel = skillCount === 1 ? '1 Habilidade' : `${skillCount} Habilidades`

  return (
    <Link
      className='group flex flex-col justify-between gap-4 rounded-2xl border border-border bg-card p-6 transition-colors hover:border-primary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40'
      params={{ goalId: id }}
      to='/learning/goals/$goalId'
    >
      <div>
        <h3 className='font-serif text-xl font-semibold text-foreground'>{title}</h3>
        <p className='mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground'>
          {description}
        </p>
      </div>
      <div className='flex items-center justify-between text-sm text-muted-foreground'>
        <span>{skillCountLabel}</span>
        <Icon
          className='transition-transform group-hover:translate-x-0.5'
          name='arrow-right'
        />
      </div>
    </Link>
  )
}
