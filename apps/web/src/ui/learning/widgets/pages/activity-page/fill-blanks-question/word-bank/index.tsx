import type { FillBlanksWord } from '@/core/learning/choice-activity'

import { BankWord } from './bank-word'
import { useWordBank } from './use-word-bank'

export type WordBankProps = {
  contentLanguage: string
  disabled: boolean
  onSelectWord: (wordKey: string) => void
  selectedWordKey: string | null
  words: readonly FillBlanksWord[]
}

export const WordBank = ({
  contentLanguage,
  disabled,
  onSelectWord,
  selectedWordKey,
  words,
}: WordBankProps) => {
  const { isOver, setNodeRef } = useWordBank()

  return (
    <section
      aria-label='Banco de palavras'
      className='fill-blanks-bank min-h-16 rounded-md border border-control-border bg-card p-3'
      data-over={isOver}
      ref={setNodeRef}
    >
      {words.length > 0 ? (
        <ul className='flex flex-wrap gap-2'>
          {words.map((word) => (
            <li key={word.key}>
              <BankWord
                contentLanguage={contentLanguage}
                disabled={disabled}
                isSelected={selectedWordKey === word.key}
                onSelect={onSelectWord}
                word={word}
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className='text-sm text-muted-foreground'>
          Todas as palavras foram colocadas nas lacunas.
        </p>
      )}
    </section>
  )
}
