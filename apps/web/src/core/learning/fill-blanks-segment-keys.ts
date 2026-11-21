import type { FillBlanksSegment } from './choice-activity'

/** Stable React keys: a blank keeps its own key, a text run is keyed by the blank before it. */
export function fillBlanksSegmentKeys(segments: readonly FillBlanksSegment[]) {
  let previousBlankKey = 'start'

  return segments.map((segment) => {
    if (segment.blankKey) {
      previousBlankKey = segment.blankKey
      return segment.blankKey
    }

    return `text-after-${previousBlankKey}`
  })
}
