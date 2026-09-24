import type { ActivityRecommendation } from '@/core/learning/competency-detail'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

const DIFFICULTY_LABELS = {
  easy: 'Fácil',
  medium: 'Média',
  hard: 'Difícil',
} as const

const RECOMMENDATION_LABELS = {
  'new-activity': 'Atividade nova',
  reinforcement: 'Reforço',
} as const

export type MaterialRecommendationProps = {
  competencyName: string
  hasFailure: boolean
  isPending: boolean
  onOpen: () => void
  recommendation: ActivityRecommendation
}

export const MaterialRecommendation = ({
  competencyName,
  hasFailure,
  isPending,
  onOpen,
  recommendation,
}: MaterialRecommendationProps) => {
  const metadata = `${RECOMMENDATION_LABELS[recommendation.type]} · ${
    DIFFICULTY_LABELS[recommendation.difficulty]
  }`

  return (
    <section
      aria-labelledby='material-recommendation-title'
      className='max-w-[68ch] rounded-md border border-border bg-card p-5'
    >
      <div className='flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between'>
        <div className='flex min-w-0 items-start gap-4'>
          <span className='grid size-11 shrink-0 place-items-center rounded-full border border-primary bg-accent text-selo-text'>
            <Icon name='target' size={20} />
          </span>
          <div className='min-w-0'>
            <h2
              className='font-semibold text-foreground'
              id='material-recommendation-title'
            >
              Continuar em {competencyName}
            </h2>
            <p className='mt-1 text-sm text-selo-text'>{metadata}</p>
          </div>
        </div>
        <Button className='shrink-0' disabled={isPending} onClick={onOpen} type='button'>
          {isPending ? 'Abrindo...' : 'Praticar'}
        </Button>
      </div>

      {hasFailure ? (
        <p
          className='mt-4 flex items-start gap-3 rounded-md border border-primary bg-accent px-3 py-3 text-sm text-selo-text'
          role='alert'
        >
          <Icon className='mt-0.5 shrink-0' name='circle-alert' size={17} />
          <span>
            Não foi possível abrir a Atividade agora. O material continua aqui — tente
            novamente.
          </span>
        </p>
      ) : null}
    </section>
  )
}
