import type { FillBlanksSegment, FillBlanksWord } from '@/core/learning/choice-activity'

import { BlankSlot } from './blank-slot'

export type FillBlanksTextProps = {
  blankNumberByKey: ReadonlyMap<string, number>
  contentLanguage: string
  disabled: boolean
  onActivateBlank: (blankKey: string) => void
  placedWordKeyByBlank: ReadonlyMap<string, string>
  segments: readonly FillBlanksSegment[]
  wordByKey: ReadonlyMap<string, FillBlanksWord>
}

export const FillBlanksText = ({
  blankNumberByKey,
  contentLanguage,
  disabled,
  onActivateBlank,
  placedWordKeyByBlank,
  segments,
  wordByKey,
}: FillBlanksTextProps) => (
  <p className='whitespace-pre-wrap rounded-md border border-border bg-card p-4 text-xl leading-[3rem] sm:p-6'>
    {segments.map((segment, index) =>
      segment.blankKey === null ? (
        // biome-ignore lint/suspicious/noArrayIndexKey: the segment order is fixed by the Curriculum.
        <span key={`text-${index}`} lang={contentLanguage}>
          {segment.text}
        </span>
      ) : (
        <BlankSlot
          blankKey={segment.blankKey}
          blankNumber={blankNumberByKey.get(segment.blankKey) ?? 0}
          contentLanguage={contentLanguage}
          disabled={disabled}
          key={segment.blankKey}
          onActivate={onActivateBlank}
          placedWord={
            wordByKey.get(placedWordKeyByBlank.get(segment.blankKey) ?? '') ?? null
          }
        />
      ),
    )}
  </p>
)
