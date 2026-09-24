import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'

export type GoalDetailHeaderProps = {
  goalId: string
  title: string
  description: string
}

export const GoalDetailHeader = ({
  goalId,
  title,
  description,
}: GoalDetailHeaderProps) => (
  <header className='flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between'>
    <div className='min-w-0 max-w-4xl'>
      <p className='text-sm font-semibold text-muted-foreground'>Objetivo</p>
      <h1 className='mt-2 break-words font-serif text-4xl tracking-tight sm:text-5xl'>
        {title}
      </h1>
      <p className='mt-4 break-words leading-7 text-muted-foreground'>{description}</p>
    </div>
    <div className='flex shrink-0 flex-wrap gap-2'>
      <Link
        className='inline-flex min-h-11 items-center rounded-md bg-primary px-4 font-semibold text-primary-foreground'
        params={{ goalId }}
        to='/learning/goals/$goalId/skills/add'
      >
        <Icon name='plus' size={17} />
        <span className='ml-2'>Adicionar Habilidade</span>
      </Link>
      <Button
        aria-describedby='remove-goal-description'
        disabled
        type='button'
        variant='ghost'
      >
        <Icon name='trash-2' size={17} />
        <span className='ml-2'>Remover objetivo</span>
      </Button>
      <p className='sr-only' id='remove-goal-description'>
        Disponível em uma próxima atualização
      </p>
    </div>
  </header>
)
