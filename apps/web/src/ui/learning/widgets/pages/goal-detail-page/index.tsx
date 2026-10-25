import { motion } from 'motion/react'

import { ENTRANCE_RISE, ENTRANCE_SECTION } from '@/constants/motion-variants'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { GoalDetailFeedback } from './goal-detail-feedback'
import { GoalAddSkillLink, GoalDetailHeader } from './goal-detail-header'
import { GoalSkillGraph } from './goal-skill-graph'
import { GoalSkillList } from './goal-skill-list'
import { GoalViewSwitcher } from './goal-view-switcher'
import { ConfirmationDialog } from '@/ui/shared/widgets/components/confirmation-dialog'
import { type GoalDetailPageProps, useGoalDetailPage } from './use-goal-detail-page'

export type { GoalDetailPageProps } from './use-goal-detail-page'

export const GoalDetailPage = (props: GoalDetailPageProps) => {
  const {
    detail,
    state,
    view,
    isRetrying,
    isConfirmDialogOpen,
    isDeletingGoal,
    deleteGoalError,
    selectedSkill,
    isRemovingSkill,
    removeSkillError,
    skillRemovalTriggerRef,
    handleRetry,
    handleViewChange,
    handleOpenConfirmDialog,
    handleCancelRemoval,
    handleConfirmRemoval,
    handleOpenSkillRemoval,
    handleCancelSkillRemoval,
    handleConfirmSkillRemoval,
  } = useGoalDetailPage(props)

  if (state === 'loading') return <GoalDetailFeedback state='loading' />
  if (state === 'not-found') return <GoalDetailFeedback state='not-found' />
  if (state === 'error')
    return (
      <GoalDetailFeedback isRetrying={isRetrying} onRetry={handleRetry} state='error' />
    )
  if (!detail) return null

  return (
    // The goal loads in the browser, so its ready branch runs the shared
    // Motion entrance; loading and error feedback appear without one.
    <MotionEntrance className='mx-auto w-full max-w-7xl space-y-7 pb-6'>
      <GoalDetailHeader
        description={detail.description}
        title={detail.title}
        isConfirmDialogOpen={isConfirmDialogOpen}
        isDeletingGoal={isDeletingGoal}
        deleteGoalError={deleteGoalError}
        onOpenConfirmDialog={handleOpenConfirmDialog}
        onCancelRemoval={handleCancelRemoval}
        onConfirmRemoval={handleConfirmRemoval}
      />
      <motion.div
        className='flex flex-wrap items-center justify-between gap-4'
        variants={ENTRANCE_RISE}
      >
        <GoalViewSwitcher onViewChange={handleViewChange} view={view} />
        <GoalAddSkillLink goalId={props.goalId} />
      </motion.div>
      {state === 'empty' ? (
        <motion.div variants={ENTRANCE_SECTION}>
          <GoalDetailFeedback goalId={props.goalId} state='empty' />
        </motion.div>
      ) : view === 'graph' ? (
        // The graph enters as one block: React Flow positions its nodes with its
        // own transforms after the asynchronous layout, so they are not staggered.
        <motion.div variants={ENTRANCE_SECTION}>
          <GoalSkillGraph
            goalId={props.goalId}
            relations={detail.relations}
            skills={detail.skills}
            title={detail.title}
            onRemoveSkill={handleOpenSkillRemoval}
          />
        </motion.div>
      ) : (
        <GoalSkillList
          goalId={props.goalId}
          onRemoveSkill={handleOpenSkillRemoval}
          skills={detail.skills}
        />
      )}
      <ConfirmationDialog
        cancelLabel='Cancelar'
        confirmLabel='Remover habilidade'
        description='Somente esta experiência será removida deste Objetivo. A Habilidade continuará disponível no Currículo e em outros Objetivos.'
        error={removeSkillError}
        icon='trash-2'
        isOpen={Boolean(selectedSkill)}
        isSubmitting={isRemovingSkill}
        itemName={selectedSkill?.name}
        losses={[
          'Diagnóstico, justificativa e evidências por Conceito',
          'Progresso, domínio e recomendações',
          'Tentativas, avaliações e resumo final',
        ]}
        onCancel={handleCancelSkillRemoval}
        onConfirm={() => void handleConfirmSkillRemoval()}
        restoreFocusRef={skillRemovalTriggerRef}
        title='Remover Habilidade?'
      />
    </MotionEntrance>
  )
}
