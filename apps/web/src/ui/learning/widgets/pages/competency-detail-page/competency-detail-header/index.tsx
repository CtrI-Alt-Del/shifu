import { Link } from '@tanstack/react-router'

import type {
  AvailableCompetencyDetail,
  CompetencyProgressStatus,
} from '@/core/learning/competency-detail'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ProgressMeter } from '@/ui/shared/widgets/components/progress-meter'

const STATUS_LABELS: Record<CompetencyProgressStatus, string> = {
  learning: 'Em aprendizado',
  developing: 'Em desenvolvimento',
  proficient: 'Proficiente',
  mastered: 'Dominada',
}

export type CompetencyDetailHeaderProps = {
  detail: AvailableCompetencyDetail
  goalId: string
  skillId: string
}

export const CompetencyDetailHeader = ({
  detail,
  goalId,
  skillId,
}: CompetencyDetailHeaderProps) => {
  const statusLabel = STATUS_LABELS[detail.status]

  return (
    <header className='space-y-5'>
      <Link
        aria-label='Voltar para a Habilidade'
        className='inline-flex min-h-11 items-center gap-2 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground'
        params={{ goalId, skillId }}
        to='/learning/goals/$goalId/skills/$skillId'
      >
        <Icon name='arrow-left' size={16} />
        <span className='sm:hidden'>{detail.skillName}</span>
        <span className='hidden sm:inline'>Voltar para a Habilidade</span>
      </Link>

      <div className='flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between'>
        <div className='min-w-0 max-w-4xl'>
          <p className='mb-3 hidden text-sm text-muted-foreground lg:block'>
            {detail.skillName}
          </p>
          <h1 className='font-serif text-4xl font-bold tracking-tight text-foreground sm:text-5xl'>
            {detail.competencyName}
          </h1>
          <div className='mt-4 flex flex-wrap items-center gap-2'>
            {detail.isFocus ? (
              <span className='inline-flex min-h-8 items-center gap-2 rounded-md bg-accent px-3 py-1 text-xs font-bold text-selo-text'>
                <Icon name='target' size={14} />
                Em foco
              </span>
            ) : null}
            <span className='inline-flex min-h-8 items-center gap-2 rounded-md bg-success/10 px-3 py-1 text-xs font-bold text-success'>
              <span aria-hidden='true' className='size-1.5 rounded-full bg-success' />
              {statusLabel}
            </span>
          </div>
        </div>

        <div className='w-full max-w-xl lg:min-w-[22rem]'>
          <ProgressMeter
            label='Progresso da Competência'
            tone='success'
            value={detail.progress}
          />
        </div>
      </div>

      {detail.focusReturned ? (
        <div className='flex items-start gap-3 rounded-md border border-border bg-card px-3 py-3 text-sm text-muted-foreground'>
          <Icon
            className='mt-0.5 shrink-0 text-muted-foreground'
            name='rotate-ccw'
            size={17}
          />
          <p>
            Esta Competência voltou a ser seu foco porque seu progresso atual precisa de
            reforço.
          </p>
        </div>
      ) : detail.isFocus ? (
        <div className='flex items-start gap-3 rounded-md bg-muted px-3 py-3 text-sm text-muted-foreground'>
          <Icon
            className='mt-0.5 shrink-0 text-muted-foreground'
            name='target'
            size={17}
          />
          <p>
            Siga a recomendação ou escolha qualquer item disponível nesta Competência.
          </p>
        </div>
      ) : (
        <div className='flex flex-col gap-3 rounded-md border border-border bg-card px-3 py-3 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between'>
          <div className='flex items-start gap-3'>
            <Icon
              className='mt-0.5 shrink-0 text-muted-foreground'
              name='target'
              size={17}
            />
            <p>As recomendações seguem a Competência em foco.</p>
          </div>
          {detail.focusCompetencyId && detail.focusCompetencyName ? (
            <Link
              className='inline-flex min-h-11 shrink-0 items-center gap-2 rounded-md px-2 font-semibold text-foreground underline-offset-4 hover:text-primary hover:underline'
              params={{
                competencyId: detail.focusCompetencyId,
                goalId,
                skillId,
              }}
              to='/learning/goals/$goalId/skills/$skillId/competencies/$competencyId'
            >
              Ir para a Competência em foco
              <Icon name='chevron-right' size={16} />
            </Link>
          ) : null}
        </div>
      )}
    </header>
  )
}
