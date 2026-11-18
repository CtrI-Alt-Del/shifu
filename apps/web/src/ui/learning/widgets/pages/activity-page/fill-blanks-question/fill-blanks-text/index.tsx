import { fillBlanksSegmentKeys } from '@/core/learning/fill-blanks-segment-keys'
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
}: FillBlanksTextProps) => {
  const segmentKeys = fillBlanksSegmentKeys(segments)

  return (
    <p className='whitespace-pre-wrap text-xl leading-[3rem]'>
      {segments.map((segment, index) =>
        !segment.blankKey ? (
          <span key={segmentKeys[index]} lang={contentLanguage}>
            {segment.text}
          </span>
        ) : (
          <BlankSlot
            blankKey={segment.blankKey}
            blankNumber={blankNumberByKey.get(segment.blankKey) ?? 0}
            contentLanguage={contentLanguage}
            disabled={disabled}
            key={segmentKeys[index]}
            onActivate={onActivateBlank}
            placedWord={
              wordByKey.get(placedWordKeyByBlank.get(segment.blankKey) ?? '') ?? null
            }
          />
        ),
      )}
    </p>
  )
}
