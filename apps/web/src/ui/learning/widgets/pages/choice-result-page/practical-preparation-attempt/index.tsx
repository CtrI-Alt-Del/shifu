import { Link } from '@tanstack/react-router'
import type { ReactNode } from 'react'

import type {
  ChoiceAttemptDetail,
  PracticalPreparationQuestion,
  PracticalPreparationResultQuestion,
} from '@/core/learning/choice-activity'
import type { ActivityRecommendation } from '@/core/learning/competency-detail'
import { DifficultyBadge } from '@/ui/learning/widgets/components/difficulty-badge'
import { PracticalPreparationBrief } from '@/ui/learning/widgets/components/practical-preparation-brief'
import { QuestionPrompt } from '@/ui/learning/widgets/components/question-prompt'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type PracticalPreparationAttemptProps = {
  activityTitle: string
  difficulty?: 'easy' | 'medium' | 'hard'
  question: PracticalPreparationQuestion
  attempt: ChoiceAttemptDetail
  result?: PracticalPreparationResultQuestion
  buildPhotoUrl?: (photoId: string) => string
  canRetry: boolean
  isRetrying: boolean
  hasRetryError: boolean
  onRetryEvaluation: () => void
  detailIds?: {
    goalId: string
    skillId: string
    competencyId: string
    activityId?: string
  }
  recommendation?: ActivityRecommendation | null
  onOpenRecommendation?: (recommendation: ActivityRecommendation) => void
  rewardBand?: ReactNode
  children?: ReactNode
}

const NUMBER_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })
const LINK_CLASS_NAME =
  'inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md border border-control-border px-4 font-semibold text-foreground transition-colors hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'
const PRIMARY_LINK_CLASS_NAME =
  'inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'

export const PracticalPreparationAttempt = ({
  activityTitle,
  attempt,
  buildPhotoUrl,
  canRetry,
  children,
  detailIds,
  difficulty,
  hasRetryError,
  isRetrying,
  onOpenRecommendation,
  onRetryEvaluation,
  question,
  recommendation,
  result,
  rewardBand,
}: PracticalPreparationAttemptProps) => {
  const idPrefix = `practical-attempt-${question.key}`
  const { status } = attempt
  const photos = (result?.photos ?? []).map((photo) => ({
    ...photo,
    label: result?.records.find(({ key }) => key === photo.recordKey)?.label ?? '',
  }))
  const backToSkillLink = detailIds ? (
    <Link
      className={LINK_CLASS_NAME}
      params={{ goalId: detailIds.goalId, skillId: detailIds.skillId }}
      to='/learning/goals/$goalId/skills/$skillId'
    >
      <Icon name='arrow-left' size={16} />
      Voltar à Habilidade
    </Link>
  ) : null
  const photosSection =
    photos.length > 0 ? (
      <section aria-labelledby={`${idPrefix}-photos`} className='space-y-2'>
        <h3 className='text-sm font-medium text-foreground' id={`${idPrefix}-photos`}>
          Fotos da tentativa
        </h3>
        <ul className='grid grid-cols-3 gap-3'>
          {photos.map((photo) => (
            <li key={photo.photoId}>
              {buildPhotoUrl ? (
                <img
                  alt={`Foto do registro: ${photo.label}`}
                  className='aspect-[3/2] w-full rounded-md border border-border object-cover'
                  height={96}
                  src={buildPhotoUrl(photo.photoId)}
                  width={144}
                />
              ) : (
                <p className='flex items-center gap-2 text-xs text-muted-foreground'>
                  <Icon name='camera' size={14} />
                  Foto indisponível
                </p>
              )}
              <p className='mt-1 truncate text-xs text-muted-foreground'>{photo.label}</p>
            </li>
          ))}
        </ul>
        <p className='text-xs text-muted-foreground'>
          Resposta enviada · somente leitura
        </p>
      </section>
    ) : null

  const reflectionSection = result?.reflection ? (
    <section aria-labelledby={`${idPrefix}-reflection`} className='space-y-2'>
      <h3 className='text-sm font-medium text-foreground' id={`${idPrefix}-reflection`}>
        Seu relato
      </h3>
      <p className='whitespace-pre-wrap rounded-md border border-border bg-muted p-3 text-sm text-foreground'>
        {result.reflection}
      </p>
      <p className='text-xs text-muted-foreground'>
        Relato escrito por você · somente leitura
      </p>
    </section>
  ) : null

  return (
    <div className='space-y-6'>
      <div className='flex flex-wrap items-center justify-between gap-x-4 gap-y-2'>
        <div className='space-y-1'>
          <h1 className='text-sm font-medium text-muted-foreground'>{activityTitle}</h1>
          {difficulty ? <DifficultyBadge difficulty={difficulty} /> : null}
        </div>
        <p className='text-sm text-muted-foreground'>
          Questão 1 de 1 · preparação prática
        </p>
      </div>
      <div className='space-y-3'>
        <QuestionPrompt id={`${idPrefix}-prompt`} prompt={question.prompt} />
      </div>
      {rewardBand}

      <div className='grid gap-8 lg:grid-cols-[minmax(0,1.36fr)_minmax(0,1fr)] lg:items-start'>
        <PracticalPreparationBrief question={question} />

        <div className='space-y-5 rounded-xl border border-border bg-card p-6'>
          {status === 'pending' ? (
            <>
              <h2 className='font-serif text-2xl text-foreground'>
                Avaliação em andamento
              </h2>
              <output aria-busy='true' aria-live='polite' className='block space-y-3'>
                <span className='flex items-center gap-2 text-sm text-muted-foreground'>
                  <Icon className='shrink-0' name='clock-3' size={16} />
                  Tentativa enviada
                </span>
                <span className='block text-sm text-foreground'>
                  Sua tentativa foi enviada. Você pode sair desta página enquanto
                  avaliamos as fotos.
                </span>
              </output>
              <section className='space-y-1 rounded-md border border-border bg-muted p-4'>
                <h3 className='flex items-center gap-2 text-sm font-medium text-foreground'>
                  <Icon className='shrink-0' name='clock-3' size={16} />
                  Você pode continuar estudando
                </h3>
                <p className='text-sm text-muted-foreground'>
                  Novas tentativas nesta Habilidade ficam pausadas até a avaliação
                  terminar. Outros conteúdos disponíveis continuam acessíveis.
                </p>
              </section>
              {photosSection}
              {backToSkillLink}
            </>
          ) : null}

          {status === 'failed' ? (
            <>
              <h2 className='font-serif text-2xl text-foreground'>
                A avaliação não pôde terminar
              </h2>
              <div className='space-y-3' role='alert'>
                <p className='flex items-center gap-2 text-sm text-muted-foreground'>
                  <Icon className='shrink-0' name='triangle-alert' size={16} />
                  Avaliação pendente
                </p>
                <p className='text-sm text-foreground'>
                  Sua tentativa e suas fotos estão preservadas. Tente concluir a avaliação
                  da mesma tentativa.
                </p>
                {attempt.failureMessage ? (
                  <p className='text-sm text-muted-foreground'>
                    {attempt.failureMessage}
                  </p>
                ) : null}
              </div>
              {photosSection}
              {canRetry || isRetrying ? (
                <Button
                  className='w-full'
                  disabled={isRetrying}
                  onClick={onRetryEvaluation}
                  type='button'
                >
                  {isRetrying ? 'Reiniciando avaliação…' : 'Tentar novamente'}
                </Button>
              ) : null}
              {hasRetryError ? (
                <output className='block text-sm text-selo-text'>
                  Não foi possível reiniciar agora. Tente novamente.
                </output>
              ) : null}
              {backToSkillLink}
            </>
          ) : null}

          {status === 'closed_without_grade' ? (
            <>
              <h2 className='font-serif text-2xl text-foreground'>
                Não foi possível avaliar estas fotos
              </h2>
              <div className='space-y-3'>
                <p className='flex items-center gap-2 text-sm text-muted-foreground'>
                  <Icon className='shrink-0' name='triangle-alert' size={16} />
                  Tentativa encerrada · sem nota
                </p>
                <p className='text-sm text-foreground'>
                  As fotos não mostraram o suficiente para avaliar. Esta tentativa foi
                  encerrada sem nota e não altera seu progresso.
                </p>
              </div>
              <section
                aria-labelledby={`${idPrefix}-adjust`}
                className='space-y-3 rounded-md border border-border bg-muted p-4'
              >
                <h3
                  className='flex items-center gap-2 text-sm font-medium text-foreground'
                  id={`${idPrefix}-adjust`}
                >
                  <Icon className='shrink-0' name='camera' size={16} />O que ajustar na
                  próxima tentativa
                </h3>
                {result?.guidance ? (
                  <p className='whitespace-pre-wrap text-sm text-muted-foreground'>
                    {result.guidance}
                  </p>
                ) : null}
                {result && result.unassessableRecords.length > 0 ? (
                  <div className='space-y-2'>
                    <p className='text-sm font-medium text-foreground'>
                      Registros a melhorar
                    </p>
                    <ul className='space-y-2'>
                      {result.unassessableRecords.map((record) => (
                        <li className='text-sm' key={record.key}>
                          <p className='font-medium text-foreground'>{record.label}</p>
                          <p className='text-muted-foreground'>{record.comment}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </section>
              {photosSection}
              {reflectionSection}
              {detailIds?.activityId ? (
                <Link
                  className={PRIMARY_LINK_CLASS_NAME}
                  params={{
                    goalId: detailIds.goalId,
                    skillId: detailIds.skillId,
                    competencyId: detailIds.competencyId,
                    activityId: detailIds.activityId,
                  }}
                  to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId'
                >
                  <Icon name='rotate-ccw' size={16} />
                  Iniciar nova tentativa
                </Link>
              ) : null}
              {backToSkillLink}
            </>
          ) : null}

          {status === 'completed' ? (
            <>
              <h2 className='font-serif text-2xl text-foreground'>Atividade avaliada</h2>
              <p className='flex items-center gap-2 text-sm text-success'>
                <Icon className='shrink-0' name='circle-check' size={16} />
                Avaliação concluída
              </p>
              <p className='text-sm text-foreground'>
                Confira os critérios observados nas fotos da sua preparação.
              </p>
              {attempt.score !== undefined && attempt.score !== null ? (
                <output
                  aria-label={`Nota da Atividade ${NUMBER_FORMATTER.format(attempt.score)} de 100`}
                  className='flex items-end gap-3 text-success'
                >
                  <span className='font-mono text-5xl font-semibold leading-none'>
                    {NUMBER_FORMATTER.format(attempt.score)}
                  </span>
                  <span className='pb-1 text-sm text-muted-foreground'>
                    de 100 · Nota da Atividade
                  </span>
                </output>
              ) : null}
              {result ? (
                <section aria-labelledby={`${idPrefix}-criteria`} className='space-y-3'>
                  <h3 className='sr-only' id={`${idPrefix}-criteria`}>
                    Critérios da avaliação
                  </h3>
                  <ul className='space-y-4'>
                    {result.criteria.map((criterion) => (
                      <li className='space-y-1 text-sm' key={criterion.key}>
                        <p className='flex flex-wrap items-baseline justify-between gap-x-3'>
                          <span className='text-foreground'>{criterion.name}</span>
                          <span className='font-mono text-xs text-success'>
                            {criterion.level === null
                              ? 'Sem nível'
                              : `${NUMBER_FORMATTER.format(criterion.level)} / 100`}
                            <span className='ml-2 text-muted-foreground'>
                              Peso {NUMBER_FORMATTER.format(criterion.weight)}%
                            </span>
                          </span>
                        </p>
                        {criterion.comment ? (
                          <p className='text-muted-foreground'>{criterion.comment}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
              <p className='text-xs text-muted-foreground'>
                O resultado será considerado no progresso da Competência. A reflexão não
                entra na nota.
              </p>
              {photosSection}
              {reflectionSection}
              {recommendation && onOpenRecommendation ? (
                <Button
                  className='w-full'
                  onClick={() => onOpenRecommendation(recommendation)}
                  type='button'
                >
                  Próxima Atividade
                </Button>
              ) : null}
              {detailIds ? (
                <Link
                  className={LINK_CLASS_NAME}
                  params={{
                    goalId: detailIds.goalId,
                    skillId: detailIds.skillId,
                    competencyId: detailIds.competencyId,
                  }}
                  to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
                >
                  <Icon name='arrow-left' size={16} />
                  Voltar para a Competência
                </Link>
              ) : null}
            </>
          ) : null}
        </div>
      </div>
      {children}
    </div>
  )
}
