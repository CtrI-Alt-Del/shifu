import { useId } from 'react'

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
  const labelId = useId()

  return (
    <section
      aria-labelledby={labelId}
      className='fill-blanks-bank min-h-16 space-y-3 rounded-md'
      data-over={isOver}
      ref={setNodeRef}
    >
      <h3 className='text-center text-sm font-medium text-muted-foreground' id={labelId}>
        Banco de palavras
      </h3>
      {words.length > 0 ? (
        <ul className='flex flex-wrap justify-center gap-2'>
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
