import { Button } from '@/ui/shadcn/button'
import { Skeleton } from '@/ui/shadcn/skeleton'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { PlanningIntentSummary } from './planning-intent-summary'
import { PlanningOutcome } from './planning-outcome'
import { PlanningProcessingNotice } from './planning-processing-notice'
import { PlanningProposalReview } from './planning-proposal-review'
import { PlanningQuestionCard } from './planning-question-card'
import { PlanningStepTrail } from './planning-step-trail'
import { type PlannerPageProps, usePlannerPage } from './use-planner-page'

import './planner-page.css'

export type { PlannerPageProps } from './use-planner-page'

const PAGE_TITLE = 'Planeje seu objetivo'
const COMPACT_ACTION = 'w-full gap-1.5 sm:w-auto lg:min-h-[38px] lg:px-[18px] lg:text-sm'
const WIDE_ACTION = 'w-full gap-1.5 sm:w-auto'

export const PlannerPage = (props: PlannerPageProps) => {
  const {
    view,
    intent,
    steps,
    stepLabel,
    currentQuestion,
    selectedOptionIds,
    guidance,
    isFirstStep,
    isLastStep,
    canSubmit,
    processingStage,
    proposal,
    errorMessage,
    restartErrorMessage,
    goalCreationNotice,
    generation,
    isSubmitting,
    isRetrying,
    isRestarting,
    isCancelling,
    questionHeadingRef,
    handleSelectSingle,
    handleToggleMultiple,
    handleGoToStep,
    handlePrevious,
    handleNext,
    handleSubmitAnswers,
    handleCancel,
    handleRetry,
    handleRestart,
    handleCreateGoal,
    handleReformulate,
    handleCreateManually,
    handleRetryLoad,
    handleReturnHome,
  } = usePlannerPage(props)

  return (
    <div className='planner-page mx-auto flex w-full max-w-7xl flex-1 flex-col lg:justify-center'>
      <div
        className={`mx-auto flex w-full flex-col gap-6 ${
          view === 'proposal' ? 'max-w-[1170px]' : 'max-w-[760px]'
        }`}
      >
        {view === 'loading' ? (
          <output
            aria-busy='true'
            aria-label='Carregando planejamento…'
            className='flex flex-col gap-6'
          >
            <Skeleton className='h-[52px] w-72 max-w-full' />
            <Skeleton className='h-[79px] w-full rounded-[10px]' />
            <Skeleton className='h-[77px] w-full rounded-[10px]' />
            <span className='sr-only'>Carregando planejamento…</span>
          </output>
        ) : null}

        {view === 'interview' && intent && currentQuestion ? (
          <>
            <PlanningIntentSummary intent={intent} />
            <PlanningStepTrail
              disabled={isSubmitting}
              label={stepLabel}
              onSelectStep={handleGoToStep}
              steps={steps}
            />
            <PlanningQuestionCard
              disabled={isSubmitting}
              guidance={guidance}
              headingRef={questionHeadingRef}
              onSelectSingle={handleSelectSingle}
              onToggleMultiple={handleToggleMultiple}
              question={currentQuestion}
              selectedOptionIds={selectedOptionIds}
            />
            {errorMessage ? (
              <p className='flex items-center gap-2 text-sm text-selo-text' role='alert'>
                <Icon className='shrink-0' name='circle-alert' size={16} />
                {errorMessage}
              </p>
            ) : null}
            <div className='flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between'>
              <Button
                className='order-2 self-center sm:order-1 sm:self-auto lg:min-h-[38px] lg:px-[18px] lg:text-sm'
                disabled={isCancelling || isSubmitting}
                onClick={() => void handleCancel()}
                type='button'
                variant='ghost'
              >
                Cancelar
              </Button>
              <div className='order-1 flex flex-col gap-2 sm:order-2 sm:flex-row sm:items-center sm:gap-2.5'>
                {!isFirstStep ? (
                  <Button
                    className={COMPACT_ACTION}
                    disabled={isSubmitting}
                    onClick={handlePrevious}
                    type='button'
                    variant='outline'
                  >
                    Anterior
                  </Button>
                ) : null}
                {isLastStep ? (
                  <Button
                    aria-busy={isSubmitting}
                    className={COMPACT_ACTION}
                    disabled={!canSubmit}
                    onClick={() => void handleSubmitAnswers()}
                    type='button'
                  >
                    {isSubmitting ? (
                      <Icon className='animate-spin' name='loader-circle' size={16} />
                    ) : null}
                    {isSubmitting ? 'Enviando…' : 'Enviar respostas'}
                  </Button>
                ) : (
                  <Button
                    className={COMPACT_ACTION}
                    disabled={isSubmitting}
                    onClick={handleNext}
                    type='button'
                  >
                    Próxima
                  </Button>
                )}
              </div>
            </div>
          </>
        ) : null}

        {view === 'processing' && intent && processingStage ? (
          <>
            <h1 className='font-serif text-3xl leading-[1.45] text-foreground lg:text-4xl'>
              {PAGE_TITLE}
            </h1>
            <PlanningIntentSummary intent={intent} />
            <PlanningProcessingNotice
              support={processingStage.support}
              title={processingStage.title}
              tone='processing'
            />
            <div className='flex items-center justify-between gap-3'>
              <Button
                className='lg:min-h-[38px] lg:px-[18px] lg:text-sm'
                disabled={isCancelling}
                onClick={() => void handleCancel()}
                type='button'
                variant='ghost'
              >
                Cancelar
              </Button>
              <Button
                aria-busy='true'
                className='gap-1.5 lg:min-h-[38px] lg:px-[18px] lg:text-sm'
                disabled
                type='button'
              >
                <Icon className='animate-spin' name='loader-circle' size={16} />
                {processingStage.busyLabel}
              </Button>
            </div>
          </>
        ) : null}

        {view === 'failed' && intent ? (
          <>
            <h1 className='font-serif text-3xl leading-[1.45] text-foreground lg:text-4xl'>
              {PAGE_TITLE}
            </h1>
            <PlanningIntentSummary intent={intent} />
            <PlanningProcessingNotice
              support='Seu planejamento permanece nesta página. Tente novamente para continuar de onde parou.'
              title='Não conseguimos continuar agora'
              tone='failure'
            />
            {errorMessage ? (
              <p className='flex items-center gap-2 text-sm text-selo-text' role='alert'>
                <Icon className='shrink-0' name='circle-alert' size={16} />
                {errorMessage}
              </p>
            ) : null}
            <div className='flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3'>
              <Button
                className={`order-2 sm:order-1 ${WIDE_ACTION}`}
                disabled={isCancelling || isRetrying}
                onClick={() => void handleCancel()}
                type='button'
                variant='ghost'
              >
                Cancelar
              </Button>
              <Button
                aria-busy={isRetrying}
                className={`order-1 sm:order-2 ${WIDE_ACTION}`}
                disabled={isRetrying || isCancelling}
                onClick={() => void handleRetry()}
                type='button'
              >
                {isRetrying ? (
                  <Icon className='animate-spin' name='loader-circle' size={16} />
                ) : null}
                {isRetrying ? 'Tentando novamente…' : 'Tentar novamente'}
              </Button>
            </div>
          </>
        ) : null}

        {view === 'out-of-scope' ? (
          <PlanningOutcome
            actions={
              <>
                <Button
                  className={COMPACT_ACTION}
                  disabled={isCancelling}
                  onClick={handleCreateManually}
                  type='button'
                  variant='outline'
                >
                  Criar manualmente
                </Button>
                <Button
                  className={COMPACT_ACTION}
                  disabled={isCancelling}
                  onClick={handleReformulate}
                  type='button'
                >
                  Reformular
                </Button>
              </>
            }
            description='O planejador ajuda a criar objetivos de aprendizagem. Esse pedido está fora desse escopo. Descreva o que você quer aprender ou desenvolver.'
            icon='compass'
            title='Vamos planejar sua aprendizagem'
            tone='neutral'
          />
        ) : null}

        {view === 'unsupported' ? (
          <PlanningOutcome
            actions={
              <>
                <Button
                  className={COMPACT_ACTION}
                  disabled={isCancelling}
                  onClick={handleReformulate}
                  type='button'
                  variant='outline'
                >
                  Reformular
                </Button>
                <Button
                  className={COMPACT_ACTION}
                  disabled={isCancelling}
                  onClick={handleCreateManually}
                  type='button'
                >
                  Criar manualmente
                </Button>
              </>
            }
            description='Nenhuma combinação do Currículo representa bem o que você descreveu. Você pode reformular a intenção ou montar o Objetivo por conta própria.'
            icon='compass'
            title='Ainda não temos Habilidades para isso'
            tone='alert'
          />
        ) : null}

        {view === 'validation-failed' ? (
          <PlanningOutcome
            actions={
              <>
                <Button
                  aria-busy={isRetrying}
                  className={`order-1 sm:order-3 ${WIDE_ACTION}`}
                  disabled={isRetrying || isCancelling}
                  onClick={() => void handleRetry()}
                  type='button'
                >
                  {isRetrying ? 'Tentando novamente…' : 'Tentar novamente'}
                </Button>
                <Button
                  className={`order-2 sm:order-2 ${WIDE_ACTION}`}
                  disabled={isRetrying || isCancelling}
                  onClick={handleReformulate}
                  type='button'
                  variant='outline'
                >
                  Reformular
                </Button>
                <Button
                  className={`order-3 sm:order-1 ${WIDE_ACTION}`}
                  disabled={isRetrying || isCancelling}
                  onClick={handleCreateManually}
                  type='button'
                  variant='ghost'
                >
                  Criar manualmente
                </Button>
                {errorMessage ? (
                  <p
                    className='order-4 flex w-full items-center justify-center gap-2 text-sm text-selo-text'
                    role='alert'
                  >
                    <Icon className='shrink-0' name='circle-alert' size={16} />
                    {errorMessage}
                  </p>
                ) : null}
              </>
            }
            actionsLayout='stack'
            description='Não conseguimos montar uma proposta para seu objetivo. Nenhum objetivo foi criado. Você pode tentar novamente, reformular sua intenção ou criar manualmente.'
            icon='shield-alert'
            title='Não conseguimos concluir sua proposta'
            tone='alert'
          />
        ) : null}

        {view === 'proposal' && intent && proposal ? (
          <PlanningProposalReview
            goalCreationNotice={goalCreationNotice}
            intent={intent}
            isCancelling={isCancelling}
            isRestarting={isRestarting}
            key={`${props.planningId}:${generation}`}
            onCancel={() => void handleCancel()}
            onCreateGoal={(request) => void handleCreateGoal(request)}
            onRestart={handleRestart}
            planningId={props.planningId}
            proposal={proposal}
            restartErrorMessage={restartErrorMessage}
          />
        ) : null}

        {view === 'not-found' ? (
          <PlanningOutcome
            actions={
              <Button className={COMPACT_ACTION} onClick={handleReturnHome} type='button'>
                Voltar à Home
              </Button>
            }
            description='Este planejamento não está mais disponível. Comece um novo pela Home.'
            icon='circle-alert'
            title='Planejamento não encontrado'
            tone='neutral'
          />
        ) : null}

        {view === 'request-error' ? (
          <PlanningOutcome
            actions={
              <>
                <Button
                  className={COMPACT_ACTION}
                  onClick={handleReturnHome}
                  type='button'
                  variant='ghost'
                >
                  Voltar à Home
                </Button>
                <Button
                  className={COMPACT_ACTION}
                  onClick={handleRetryLoad}
                  type='button'
                >
                  Tentar novamente
                </Button>
              </>
            }
            description='O Shifu não respondeu agora. Seu planejamento continua guardado; tente novamente.'
            icon='triangle-alert'
            title='Não foi possível carregar o planejamento'
            tone='alert'
          />
        ) : null}
      </div>
    </div>
  )
}
