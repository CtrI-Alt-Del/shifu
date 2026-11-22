import type { ComparisonView } from '../use-skill-completion'

export type SkillCompletionScoreChangeProps = {
  comparison: Pick<
    ComparisonView,
    'initialText' | 'finalText' | 'sign' | 'signLabel' | 'finalTone'
  >
  className?: string
}

export const SkillCompletionScoreChange = ({
  comparison,
  className = '',
}: SkillCompletionScoreChangeProps) => {
  return (
    <span
      className={`flex shrink-0 items-center justify-end gap-2 font-mono lg:w-[100px] ${className}`}
    >
      <span className='text-sm leading-[1.2] text-muted-foreground'>
        {comparison.initialText}
      </span>
      <span aria-hidden='true' className='text-sm leading-[1.2] text-muted-foreground'>
        {comparison.sign}
      </span>
      <span className='sr-only'>{comparison.signLabel}</span>
      <span
        className={`text-base font-semibold leading-[1.2] ${
          comparison.finalTone === 'rose' ? 'text-jade-text' : 'text-foreground'
        }`}
      >
        {comparison.finalText}
      </span>
    </span>
  )
}
