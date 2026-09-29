import { useEffect, useState } from 'react'

import type { ActivityDifficulty } from '@/core/learning/competency-detail'
import { DifficultyBadge } from '@/ui/learning/widgets/components/difficulty-badge'

type ActivityQuestionHeaderProps = {
  activityTitle?: string
  difficulty?: ActivityDifficulty
  questionNumber: number
  totalQuestions: number
  questionContext?: string
  showQuestionProgress?: boolean
}

export const ActivityQuestionHeader = ({
  activityTitle,
  difficulty,
  questionNumber,
  totalQuestions,
  questionContext,
  showQuestionProgress = true,
}: ActivityQuestionHeaderProps) => {
  const completedPercent = Math.round(
    ((questionNumber - 1) / Math.max(totalQuestions, 1)) * 100,
  )
  const previousPercent = Math.round(
    (Math.max(questionNumber - 2, 0) / Math.max(totalQuestions, 1)) * 100,
  )
  const [animatedPercent, setAnimatedPercent] = useState(previousPercent)

  useEffect(() => {
    const timer = window.setTimeout(() => setAnimatedPercent(completedPercent), 0)
    return () => window.clearTimeout(timer)
  }, [completedPercent])

  return (
    <div className='shrink-0 space-y-2'>
      <div className='flex min-h-10 flex-wrap items-center justify-between gap-x-4 gap-y-2'>
        <div className='space-y-1'>
          {activityTitle ? (
            <h1 className='text-sm font-medium text-muted-foreground'>{activityTitle}</h1>
          ) : null}
          {difficulty ? <DifficultyBadge difficulty={difficulty} /> : null}
        </div>
        <p className='text-sm text-muted-foreground'>
          {showQuestionProgress ? (
            <span>
              Questão {questionNumber} de {totalQuestions}
            </span>
          ) : null}
          {questionContext ? (
            <>
              {showQuestionProgress ? <span aria-hidden='true'> · </span> : null}
              <span>{questionContext}</span>
            </>
          ) : null}
        </p>
      </div>
      {showQuestionProgress ? (
        <div
          aria-label='Progresso da Atividade'
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={completedPercent}
          aria-valuetext={`${questionNumber - 1} de ${totalQuestions} questões concluídas`}
          className='mx-4 h-1 overflow-hidden bg-muted'
          role='progressbar'
        >
          <div
            className='h-full bg-success transition-[width] duration-700 ease-out motion-reduce:transition-none'
            style={{ width: `${animatedPercent}%` }}
          />
        </div>
      ) : null}
    </div>
  )
}
