import { Link } from '@tanstack/react-router'

import { Icon } from '@/ui/shared/widgets/components/icon'
import { Button } from '@/ui/shadcn/button'
import { ConfirmationDialog } from '@/ui/shared/widgets/components/confirmation-dialog'

export type GoalDetailHeaderProps = {
  title: string
  description: string
  isConfirmDialogOpen: boolean
  isDeletingGoal: boolean
  deleteGoalError: string | null
  onOpenConfirmDialog: () => void
  onCancelRemoval: () => void
  onConfirmRemoval: () => void
}

export const GoalDetailHeader = ({
  title,
  description,
  isConfirmDialogOpen,
  isDeletingGoal,
  deleteGoalError,
  onOpenConfirmDialog,
  onCancelRemoval,
  onConfirmRemoval,
}: GoalDetailHeaderProps) => (
  <header className='flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between'>
    <div className='min-w-0 max-w-4xl'>
      <h1 className='break-words font-serif text-4xl font-normal tracking-tight sm:text-[40px]'>
        {title}
      </h1>
      <p className='mt-2 break-words leading-6 text-foreground/80'>{description}</p>
    </div>
    <div className='flex shrink-0 flex-wrap gap-2'>
      <Button
        className='text-selo-text'
        onClick={onOpenConfirmDialog}
        type='button'
        variant='ghost'
      >
        <Icon name='trash-2' size={17} />
        <span className='ml-2'>Remover objetivo</span>
      </Button>
    </div>

    <ConfirmationDialog
      title='Remover este objetivo?'
      itemName={title}
      description='Todas as habilidades vinculadas e seus diagnósticos, progresso, tentativas, avaliações e resumos serão apagados permanentemente.'
      confirmLabel='Remover objetivo'
      cancelLabel='Cancelar'
      icon='trash-2'
      isOpen={isConfirmDialogOpen}
      isSubmitting={isDeletingGoal}
      error={deleteGoalError}
      onConfirm={onConfirmRemoval}
      onCancel={onCancelRemoval}
    />
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
