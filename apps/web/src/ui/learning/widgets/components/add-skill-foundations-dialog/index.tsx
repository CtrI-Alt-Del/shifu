import type { ReactNode } from 'react'

import type { SuggestedFoundation } from '@/core/learning/suggested-foundation'
import { Button } from '@/ui/shadcn/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/ui/shadcn/dialog'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { OtherGoalExperienceNotice } from '../other-goal-experience-notice'
import { SkillFoundationRow } from '../skill-foundation-row'
import { useAddSkillFoundationsDialog } from './use-add-skill-foundations-dialog'

export type AddSkillFoundationsDialogProps = {
  goalId: string
  skillId: string
  skillName: string
  foundations: readonly SuggestedFoundation[]
  isOpen: boolean
  isLoading?: boolean
  error?: string | null
  onClose: () => void
  onSubmit: (selectedFoundationIds: readonly string[]) => Promise<void>
}

export const AddSkillFoundationsDialog = ({
  goalId,
  skillId,
  skillName,
  foundations,
  isOpen,
  isLoading = false,
  error = null,
  onClose,
  onSubmit,
}: AddSkillFoundationsDialogProps): ReactNode => {
  const {
    description,
    hasFoundations,
    isSubmitting,
    missingFoundations,
    note,
    otherGoalExperiences,
    presentFoundations,
    isFoundationSelected,
    handleCloseAutoFocus,
    handleOpenChange,
    handleSubmit,
    handleToggle,
  } = useAddSkillFoundationsDialog({ goalId, skillId, foundations, onClose, onSubmit })

  return (
    <Dialog onOpenChange={handleOpenChange} open={isOpen}>
      <DialogContent
        className='flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2.5rem)]! max-w-[480px]! flex-col gap-4 overflow-y-auto rounded-[14px]! bg-card'
        onCloseAutoFocus={handleCloseAutoFocus}
      >
        <DialogClose
          aria-label='Fechar'
          className='absolute right-2 top-2 inline-flex size-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-50 sm:right-4 sm:top-4 sm:size-6 sm:rounded-md'
          disabled={isSubmitting}
          type='button'
        >
          <Icon className='size-4' name='x' />
        </DialogClose>
        <DialogHeader className='mb-0! flex-row! gap-3 space-y-0! border-b border-border pb-4 pr-8 text-left! sm:pr-8'>
          <div className='flex size-11 shrink-0 items-center justify-center rounded-full bg-accent'>
            <Icon className='size-[17px] text-selo-text' name='graduation-cap' />
          </div>
          <div className='flex min-w-0 flex-col gap-1'>
            <DialogTitle className='text-lg font-semibold leading-snug text-foreground'>
              Adicionar {skillName}?
            </DialogTitle>
            <DialogDescription className='text-[15px] leading-snug text-secondary-foreground'>
              {description}
            </DialogDescription>
          </div>
        </DialogHeader>

        {isLoading ? (
          <output className='block py-4 text-center text-sm text-muted-foreground'>
            Carregando...
          </output>
        ) : null}

        {!isLoading && hasFoundations ? (
          <div className='max-h-72 space-y-5 overflow-y-auto'>
            {missingFoundations.length > 0 ? (
              <section>
                <h3 className='mb-3 text-sm font-semibold text-secondary-foreground'>
                  Bases ausentes ({missingFoundations.length})
                </h3>
                <div className='space-y-2'>
                  {missingFoundations.map((foundation) => (
                    <SkillFoundationRow
                      isSelectable
                      isSelected={isFoundationSelected(foundation.skillId)}
                      key={foundation.skillId}
                      name={foundation.name}
                      onToggle={handleToggle}
                      skillId={foundation.skillId}
                      status='missing'
                    />
                  ))}
                </div>
              </section>
            ) : null}
            {presentFoundations.length > 0 ? (
              <section>
                <h3 className='mb-3 text-sm font-semibold text-secondary-foreground'>
                  Bases já presentes ({presentFoundations.length})
                </h3>
                <div className='space-y-2'>
                  {presentFoundations.map((foundation) => (
                    <SkillFoundationRow
                      isSelectable={false}
                      key={foundation.skillId}
                      name={foundation.name}
                      skillId={foundation.skillId}
                      status='present'
                    />
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        ) : null}

        <OtherGoalExperienceNotice experiences={otherGoalExperiences} />

        {error ? (
          <div className='text-sm text-selo-text' role='alert'>
            {error}
          </div>
        ) : null}

        <p className='text-[13px] text-muted-foreground'>{note}</p>

        <DialogFooter className='[&&]:mt-0! flex-row! justify-end! gap-3 border-t-0! pt-0! space-x-0!'>
          <DialogClose asChild>
            <Button
              className='border-control-border! text-foreground!'
              disabled={isSubmitting}
              type='button'
              variant='outline'
            >
              Cancelar
            </Button>
          </DialogClose>
          <Button
            disabled={isSubmitting}
            onClick={() => void handleSubmit()}
            type='button'
          >
            {isSubmitting ? 'Adicionando...' : 'Adicionar habilidade'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
