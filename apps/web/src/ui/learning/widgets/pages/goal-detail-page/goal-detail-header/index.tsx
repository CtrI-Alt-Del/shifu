import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'

export type GoalDetailHeaderProps = {
  title: string
  description: string
}

export const GoalDetailHeader = ({ title, description }: GoalDetailHeaderProps) => (
  <header className='flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between'>
    <div className='min-w-0 max-w-4xl'>
      <h1 className='break-words font-serif text-4xl font-normal tracking-tight sm:text-[40px]'>
        {title}
      </h1>
      <p className='mt-2 break-words leading-6 text-foreground/80'>{description}</p>
    </div>
    <div className='flex shrink-0 flex-wrap gap-2'>
      <Button
        aria-describedby='remove-goal-description'
        className='text-selo-text disabled:opacity-100'
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

export const GoalAddSkillLink = ({ goalId }: { goalId: string }) => (
  <Link
    className='inline-flex min-h-11 items-center rounded-md bg-primary px-[18px] font-semibold text-primary-foreground'
    params={{ goalId }}
    to='/learning/goals/$goalId/skills/add'
  >
    Adicionar Habilidade
  </Link>
)
