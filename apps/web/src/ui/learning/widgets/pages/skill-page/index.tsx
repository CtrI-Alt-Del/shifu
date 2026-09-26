import { Link } from '@tanstack/react-router'

import { Button } from '@/ui/shadcn/button'
import { SkillActionsMenu } from '@/ui/learning/widgets/components/skill-actions-menu'
import { ConfirmationDialog } from '@/ui/shared/widgets/components/confirmation-dialog'

import { SkillExperience } from './skill-experience'
import { type SkillPageProps, useSkillPage } from './use-skill-page'
import { useSkillExperience } from './use-skill-experience'

export type { SkillPageProps } from './use-skill-page'

export const SkillPage = (props: SkillPageProps) => {
  const {
    diagnostic,
    skillName,
    isLoading,
    isPrivateAbsence,
    isRecoverableError,
    isStarting,
    startError,
    isRetrying,
    retryError,
    isRemovalDialogOpen,
    isRemovingSkill,
    removeSkillError,
    removalTriggerRef,
    handleStart,
    handleRetryDiagnostic,
    handleRetry,
    handleOpenRemovalDialog,
    handleCancelRemoval,
    handleConfirmRemoval,
  } = useSkillPage(props)
  const {
    experience,
    handleRetryEvaluation,
    isExperienceLoading,
    isRetrying: isRetryingEvaluation,
    retryFailed,
  } = useSkillExperience(props)
  const isLearning =
    diagnostic?.status === 'learning' || diagnostic?.status === 'completed'

  if (isLearning && experience)
    return (
      <>
        <SkillExperience
          experience={experience}
          isRetrying={isRetryingEvaluation}
          onRetryEvaluation={() => void handleRetryEvaluation()}
          retryFailed={retryFailed}
          onRemove={handleOpenRemovalDialog}
        />
        <ConfirmationDialog
          cancelLabel='Cancelar'
          confirmLabel='Remover habilidade'
          description='Somente esta experiência será removida deste Objetivo. A Habilidade continuará disponível no Currículo e em outros Objetivos.'
          error={removeSkillError}
          icon='trash-2'
          isOpen={isRemovalDialogOpen}
          isSubmitting={isRemovingSkill}
          itemName={skillName}
          losses={[
            'Diagnóstico, justificativa e evidências por Conceito',
            'Progresso, domínio e recomendações',
            'Tentativas, avaliações e resumo final',
          ]}
          onCancel={handleCancelRemoval}
          onConfirm={() => void handleConfirmRemoval()}
          restoreFocusRef={removalTriggerRef}
          title='Remover Habilidade?'
        />
      </>
    )

  if (isLoading || (isLearning && isExperienceLoading))
    return (
      <output className='mx-auto block w-full max-w-7xl'>Carregando Habilidade...</output>
    )
  if (isPrivateAbsence)
    return (
      <h1 className='mx-auto w-full max-w-7xl font-serif text-3xl'>
        Habilidade não encontrada
      </h1>
    )
  if (isRecoverableError || !diagnostic)
    return (
      <section role='alert' className='mx-auto w-full max-w-7xl space-y-4'>
        <h1 className='font-serif text-3xl'>Não foi possível carregar a Habilidade</h1>
        <Button onClick={() => void handleRetry()} type='button'>
          Tentar novamente
        </Button>
      </section>
    )

  return (
    <main className='mx-auto w-full max-w-7xl space-y-8 pb-10'>
      <div className='mx-auto w-full max-w-4xl space-y-8'>
        <header className='flex items-start justify-between gap-4'>
          <div>
            <Link
              className='inline-flex min-h-11 items-center text-sm text-muted-foreground hover:text-foreground'
              params={{ goalId: props.goalId }}
              to='/learning/goals/$goalId'
            >
              Voltar para o Objetivo
            </Link>
            <p className='mt-4 text-xs font-bold uppercase tracking-[0.12em] text-primary'>
              Habilidade
            </p>
            <h1 className='mt-2 font-serif text-4xl font-semibold'>{skillName}</h1>
          </div>
          <SkillActionsMenu onRemove={handleOpenRemovalDialog} skillName={skillName} />
        </header>
        {diagnostic.status === 'not-started' ? (
          <section className='rounded-md border border-border bg-card p-6'>
            <h2 className='font-serif text-2xl font-semibold'>Comece pelo diagnóstico</h2>
            <p className='mt-3 text-muted-foreground'>
              O diagnóstico percorre todas as Competências desta Habilidade. Você verá
              apenas o resultado consolidado ao final.
            </p>
            {startError ? (
              <p className='mt-4 text-sm text-destructive' role='alert'>
                {startError}
              </p>
            ) : null}
            <Button
              className='mt-6'
              disabled={isStarting}
              onClick={() => void handleStart()}
              type='button'
            >
              {isStarting ? 'Iniciando...' : 'Iniciar Habilidade'}
            </Button>
          </section>
        ) : null}
        {diagnostic.status === 'diagnosing' ? (
          <section className='rounded-md border border-border bg-card p-6'>
            <p className='text-xs font-bold uppercase tracking-[0.12em] text-primary'>
              Diagnóstico em andamento
            </p>
            <h2 className='mt-2 font-serif text-2xl font-semibold'>
              Seu ponto de partida
            </h2>
            <p className='mt-3 text-muted-foreground'>
              As respostas são avaliadas em conjunto. Notas e correções individuais não
              aparecem durante o diagnóstico.
            </p>
            {diagnostic.pendingAttemptStatus === 'failed' ? (
              <div
                className='mt-5 space-y-3 rounded-md border border-border bg-muted p-4'
                role='alert'
              >
                <p>
                  A avaliação desta resposta falhou no Shifu. Sua resposta enviada foi
                  preservada.
                </p>
                {retryError ? <p>Não foi possível tentar novamente agora.</p> : null}
                <Button
                  disabled={isRetrying}
                  onClick={() => void handleRetryDiagnostic()}
                  type='button'
                >
                  {isRetrying ? 'Tentando novamente...' : 'Tentar avaliação novamente'}
                </Button>
              </div>
            ) : diagnostic.pendingAttemptStatus === 'pending' ? (
              <output className='mt-5 block rounded-md bg-muted p-4'>
                Aguardando a avaliação da última resposta. Esta página será atualizada
                automaticamente.
              </output>
            ) : diagnostic.nextActivityId && diagnostic.nextCompetencyId ? (
              <Link
                className='mt-6 inline-flex min-h-11 items-center rounded-md bg-primary px-5 font-semibold text-primary-foreground hover:bg-primary/90'
                params={{
                  goalId: props.goalId,
                  skillId: props.skillId,
                  competencyId: diagnostic.nextCompetencyId,
                  activityId: diagnostic.nextActivityId,
                }}
                to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId'
              >
                Continuar diagnóstico
              </Link>
            ) : (
              <output className='mt-5 block'>Preparando a próxima Atividade...</output>
            )}
          </section>
        ) : null}
        {diagnostic.status === 'learning' || diagnostic.status === 'completed' ? (
          <section aria-labelledby='diagnostic-summary-title' className='space-y-5'>
            <div>
              <p className='text-xs font-bold uppercase tracking-[0.12em] text-primary'>
                Diagnóstico concluído
              </p>
              <h2
                className='mt-2 font-serif text-2xl font-semibold'
                id='diagnostic-summary-title'
              >
                Seu ponto de partida por Competência
              </h2>
              <p className='mt-2 text-sm text-muted-foreground'>
                Este é o resumo consolidado. Respostas e correções individuais não são
                exibidas.
              </p>
            </div>
            <ul className='space-y-3'>
              {diagnostic.competencies.map((competency) => (
                <li
                  className='rounded-md border border-border bg-card p-5'
                  key={competency.competencyId}
                >
                  <div className='flex flex-col justify-between gap-3 sm:flex-row sm:items-center'>
                    <div>
                      <h3 className='font-semibold'>{competency.competencyName}</h3>
                    </div>
                    <p className='font-mono text-xl font-semibold'>
                      {competency.progress === null
                        ? 'Sem evidência'
                        : `${Math.round(competency.progress)}%`}
                    </p>
                  </div>
                  <Link
                    className='mt-3 inline-flex min-h-11 items-center text-sm font-semibold text-primary underline-offset-4 hover:underline'
                    params={{
                      goalId: props.goalId,
                      skillId: props.skillId,
                      competencyId: competency.competencyId,
                    }}
                    to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
                  >
                    Ver Competência
                  </Link>
                </li>
              ))}
            </ul>
            {diagnostic.focusCompetencyId ? (
              <Link
                className='inline-flex min-h-11 items-center rounded-md bg-primary px-5 font-semibold text-primary-foreground hover:bg-primary/90'
                params={{
                  goalId: props.goalId,
                  skillId: props.skillId,
                  competencyId: diagnostic.focusCompetencyId,
                }}
                to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
              >
                Continuar aprendizagem
              </Link>
            ) : null}
          </section>
        ) : null}
      </div>
      <ConfirmationDialog
        cancelLabel='Cancelar'
        confirmLabel='Remover habilidade'
        description='Somente esta experiência será removida deste Objetivo. A Habilidade continuará disponível no Currículo e em outros Objetivos.'
        error={removeSkillError}
        icon='trash-2'
        isOpen={isRemovalDialogOpen}
        isSubmitting={isRemovingSkill}
        itemName={skillName}
        losses={[
          'Diagnóstico, justificativa e evidências por Conceito',
          'Progresso, domínio e recomendações',
          'Tentativas, avaliações e resumo final',
        ]}
        onCancel={handleCancelRemoval}
        onConfirm={() => void handleConfirmRemoval()}
        restoreFocusRef={removalTriggerRef}
        title='Remover Habilidade?'
      />
    </main>
  )
}
