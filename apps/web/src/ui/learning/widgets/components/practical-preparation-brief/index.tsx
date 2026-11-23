import type { PracticalPreparationQuestion } from '@/core/learning/choice-activity'

export type PracticalPreparationBriefProps = {
  question: PracticalPreparationQuestion
}

const WEIGHT_FORMATTER = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 })

export const PracticalPreparationBrief = ({
  question,
}: PracticalPreparationBriefProps) => {
  const idPrefix = `practical-brief-${question.key}`

  return (
    <div className='space-y-8'>
      {question.guidance.length > 0 || question.references.length > 0 ? (
        <section aria-labelledby={`${idPrefix}-prepare`} className='space-y-3'>
          <h2 className='text-lg font-medium text-foreground' id={`${idPrefix}-prepare`}>
            O que você vai preparar
          </h2>
          {question.guidance.length > 0 ? (
            <ul className='space-y-2 text-sm text-foreground'>
              {question.guidance.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
          {question.references.length > 0 ? (
            <div className='space-y-1'>
              <h3 className='text-sm font-medium text-muted-foreground'>Referências</h3>
              <ul className='space-y-1 text-sm text-muted-foreground'>
                {question.references.map((reference) => (
                  <li key={reference.label}>
                    <span className='font-medium'>{reference.label}</span>
                    {reference.accessibleText ? (
                      <span>: {reference.accessibleText}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      <section
        aria-labelledby={`${idPrefix}-criteria`}
        className='space-y-3 border-t border-border pt-6'
      >
        <h2 className='text-lg font-medium text-foreground' id={`${idPrefix}-criteria`}>
          O que será avaliado
        </h2>
        <ul className='space-y-3'>
          {question.criteria.map((criterion) => (
            <li className='text-sm' key={criterion.key}>
              <p className='flex flex-wrap items-baseline justify-between gap-x-3'>
                <span className='text-foreground'>{criterion.name}</span>
                <span className='font-mono text-xs text-muted-foreground'>
                  Peso {WEIGHT_FORMATTER.format(criterion.weight)}%
                </span>
              </p>
              <p className='text-xs text-muted-foreground'>{criterion.description}</p>
            </li>
          ))}
        </ul>
        <p className='text-xs text-muted-foreground'>
          A avaliação considera apenas o que as fotos permitem observar.
        </p>
      </section>
    </div>
  )
}
