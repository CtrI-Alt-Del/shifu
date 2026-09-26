import type { SkillEvaluationState } from '@/core/learning/skill-experience'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type SkillEvaluationNoticeProps = {
  evaluation: SkillEvaluationState
  isRetrying: boolean
  onRetry: () => void
  retryFailed: boolean
}

export const SkillEvaluationNotice = ({
  evaluation,
  isRetrying,
  onRetry,
  retryFailed,
}: SkillEvaluationNoticeProps) => {
  if (evaluation.status === 'pending') {
    return (
      <output
        aria-live='polite'
        className='flex flex-wrap items-center gap-3.5 rounded-[10px] bg-surface-alt p-4 xl:flex-nowrap'
      >
        <span aria-hidden='true' className='flex shrink-0 items-center gap-1.5'>
          <span className='size-2 rounded-full bg-jade-solid' />
          <span className='size-2 rounded-full bg-jade-fill' />
          <span className='size-2 rounded-full bg-jade-tint' />
        </span>
        <span className='shrink-0 text-lg text-foreground'>Avaliando sua resposta</span>
        <span className='text-sm text-secondary-foreground xl:flex-1'>
          Novas tentativas desta Habilidade estão pausadas. Você ainda pode consultar as
          Competências e conteúdos já liberados.
        </span>
      </output>
    )
  }

  return (
    <section
      className='flex flex-wrap items-center gap-3.5 rounded-[10px] border border-selo-text bg-surface-alt p-4 xl:flex-nowrap'
      role='alert'
    >
      <span className='grid size-9 shrink-0 place-items-center rounded-[18px] bg-accent text-selo-text'>
        <Icon name='circle-alert' size={18} />
      </span>
      <span className='shrink-0 text-lg text-foreground'>
        A avaliação não pôde terminar
      </span>
      <span className='text-sm text-secondary-foreground xl:flex-1'>
        Sua resposta foi preservada. Tente avaliar novamente; as Competências e conteúdos
        liberados continuam disponíveis.
      </span>
      <button
        className='inline-flex min-h-[38px] shrink-0 items-center rounded-md bg-primary px-[18px] text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-70'
        disabled={isRetrying}
        onClick={onRetry}
        type='button'
      >
        {isRetrying ? 'Tentando...' : 'Tentar novamente'}
      </button>
      {retryFailed ? (
        <span className='w-full text-sm text-selo-text'>
          Não foi possível reprocessar agora. Tente novamente em instantes.
        </span>
      ) : null}
    </section>
  )
}
