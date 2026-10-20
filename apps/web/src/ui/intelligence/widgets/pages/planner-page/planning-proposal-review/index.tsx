import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'
import { Tabs, TabsList, TabsTrigger } from '@/ui/shadcn/tabs'
import { Textarea } from '@/ui/shadcn/textarea'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { PlanningProcessingNotice } from '../planning-processing-notice'
import { ProposalSkillGraph } from './proposal-skill-graph'
import { ProposalSkillList } from './proposal-skill-list'
import { RestartPlanningDialog } from './restart-planning-dialog'
import {
  type PlanningProposalReviewProps,
  usePlanningProposalReview,
} from './use-planning-proposal-review'

export type {
  GoalCreationState,
  GoalCreationStatus,
  PlanningProposalReviewProps,
} from './use-planning-proposal-review'

const COMPACT_ACTION = 'w-full gap-1.5 sm:w-auto lg:min-h-[38px] lg:px-[18px] lg:text-sm'

export const PlanningProposalReview = (props: PlanningProposalReviewProps) => {
  const {
    intent,
    proposal,
    isCancelling,
    isRestarting,
    restartErrorMessage,
    goalCreation,
    onCancel,
  } = props
  const {
    view,
    title,
    description,
    titleError,
    descriptionError,
    relationSummary,
    isRestartDialogOpen,
    isFrozen,
    createGoalLabel,
    goalCreationNotice,
    titleRef,
    descriptionRef,
    restartTriggerRef,
    handleViewChange,
    handleTitleChange,
    handleDescriptionChange,
    handleCreateGoal,
    handleOpenRestart,
    handleCloseRestart,
    handleSubmitRestart,
  } = usePlanningProposalReview(props)
  const isBusy = isCancelling || isRestarting
  const isCreating = goalCreation.status === 'creating'

  return (
    <section aria-labelledby='planning-review-title' className='flex flex-col gap-5'>
      <div className='flex flex-col gap-5'>
        <h1
          className='font-serif text-3xl leading-[1.3] text-foreground lg:text-4xl'
          id='planning-review-title'
        >
          Revise seu objetivo
        </h1>
        {goalCreationNotice ? (
          <PlanningProcessingNotice
            support={goalCreationNotice.support}
            title={goalCreationNotice.title}
            tone={goalCreationNotice.tone}
          />
        ) : null}
        <p className='text-sm leading-[1.45] text-secondary-foreground'>
          Esta proposta considera o que você quer alcançar e as respostas deste
          planejamento.
        </p>
      </div>

      <div className='flex flex-col gap-1.5'>
        <Label
          className='text-[13px] font-semibold text-secondary-foreground'
          htmlFor='planning-review-title-field'
        >
          Título
        </Label>
        <Input
          aria-describedby={titleError ? 'planning-review-title-error' : undefined}
          aria-invalid={Boolean(titleError)}
          className='min-h-[52px] px-4 text-[15px]'
          disabled={isFrozen}
          id='planning-review-title-field'
          onChange={(event) => handleTitleChange(event.target.value)}
          ref={titleRef}
          value={title}
        />
        {titleError ? (
          <p
            className='flex items-center gap-2 text-sm text-selo-text'
            id='planning-review-title-error'
            role='alert'
          >
            <Icon className='shrink-0' name='circle-alert' size={16} />
            {titleError}
          </p>
        ) : null}
      </div>

      <div className='flex flex-col gap-1.5'>
        <Label
          className='text-[13px] font-semibold text-secondary-foreground'
          htmlFor='planning-review-description-field'
        >
          Descrição
        </Label>
        <Textarea
          aria-describedby={
            descriptionError ? 'planning-review-description-error' : undefined
          }
          aria-invalid={Boolean(descriptionError)}
          className='min-h-[88px] resize-none px-4 py-3.5 text-[15px] leading-[1.45]'
          disabled={isFrozen}
          id='planning-review-description-field'
          onChange={(event) => handleDescriptionChange(event.target.value)}
          ref={descriptionRef}
          rows={3}
          value={description}
        />
        {descriptionError ? (
          <p
            className='flex items-center gap-2 text-sm text-selo-text'
            id='planning-review-description-error'
            role='alert'
          >
            <Icon className='shrink-0' name='circle-alert' size={16} />
            {descriptionError}
          </p>
        ) : null}
      </div>

      <div className='flex flex-col gap-2'>
        <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
          <h2 className='text-lg font-semibold leading-[1.45] text-foreground'>
            Habilidades sugeridas
          </h2>
          <Tabs onValueChange={handleViewChange} value={view}>
            <TabsList
              aria-label='Modo de visualização das Habilidades'
              className='min-h-[52px] border-0'
            >
              <TabsTrigger className='min-h-11 px-3 text-[13px]' value='graph'>
                Grafo
              </TabsTrigger>
              <TabsTrigger className='min-h-11 px-3 text-[13px]' value='list'>
                Lista
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        <p className='text-[13px] leading-[1.45] text-secondary-foreground'>
          {relationSummary}
        </p>
      </div>

      {view === 'graph' ? (
        <ProposalSkillGraph
          relations={proposal.relations}
          skills={proposal.skills}
          title={title.trim() || proposal.title}
        />
      ) : (
        <ProposalSkillList skills={proposal.skills} />
      )}

      <p className='text-[13px] leading-[1.45] text-secondary-foreground'>
        Quer mudar as habilidades ou o foco? Reinicie o planejamento com uma nova
        intenção.
      </p>

      <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
        <Button
          className='order-2 self-center sm:order-1 sm:self-auto lg:min-h-[38px] lg:px-[18px] lg:text-sm'
          disabled={isBusy || isFrozen}
          onClick={onCancel}
          type='button'
          variant='ghost'
        >
          Cancelar
        </Button>
        <div className='order-1 flex flex-col gap-2 sm:order-2 sm:flex-row sm:items-center sm:gap-2.5'>
          <Button
            className={COMPACT_ACTION}
            disabled={isBusy || isFrozen}
            onClick={handleOpenRestart}
            ref={restartTriggerRef}
            type='button'
            variant='outline'
          >
            Reiniciar planejamento
          </Button>
          <Button
            aria-busy={isCreating}
            className={`${COMPACT_ACTION} ${
              // The mobile failure frame leads with the retry; the DOM order stays the same.
              goalCreation.status === 'failed' ? 'order-first sm:order-none' : ''
            }`}
            disabled={isBusy || isCreating}
            onClick={handleCreateGoal}
            type='button'
          >
            {isCreating ? (
              <Icon className='animate-spin' name='loader-circle' size={16} />
            ) : null}
            {createGoalLabel}
          </Button>
        </div>
      </div>

      <RestartPlanningDialog
        errorMessage={restartErrorMessage}
        initialIntent={intent}
        isOpen={isRestartDialogOpen}
        isSubmitting={isRestarting}
        onClose={handleCloseRestart}
        onSubmit={(initialIntent) => void handleSubmitRestart(initialIntent)}
        restoreFocusRef={restartTriggerRef}
      />
    </section>
  )
}
