import { cleanup, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type {
  PairMatchingQuestion,
  PairMatchingResultQuestion,
} from '@/core/learning/choice-activity'

import { usePairMatchingResult } from '../use-pair-matching-result'

const QUESTION: PairMatchingQuestion = {
  key: 'pairs-1',
  kind: 'pair_matching',
  prompt: 'Associe.',
  sourceLanguage: 'en',
  targetLanguage: 'pt-BR',
  words: [
    { key: 'w0', text: 'dog' },
    { key: 'w1', text: 'house' },
  ],
  translations: [
    { key: 't1', text: 'casa' },
    { key: 't0', text: 'cachorro' },
  ],
}

function result(
  overrides: Partial<PairMatchingResultQuestion> = {},
): PairMatchingResultQuestion {
  return {
    key: 'pairs-1',
    kind: 'pair_matching',
    prompt: 'Associe.',
    score: 50,
    submittedPairs: [
      { wordKey: 'w0', translationKey: 't0' },
      { wordKey: 'w1', translationKey: 't0' },
    ],
    correctPairCount: 1,
    totalPairCount: 2,
    outcome: 'partial',
    explanation: 'Alguns pares estão corretos.',
    ...overrides,
  }
}

describe('usePairMatchingResult', () => {
  afterEach(cleanup)

  it('resolves the submitted pairs to their texts and formats the grade in pt-BR', () => {
    const { result: hook } = renderHook(() =>
      usePairMatchingResult({
        question: QUESTION,
        questionNumber: 3,
        result: result({ score: 66.67 }),
      }),
    )

    expect(hook.current.submittedItems).toEqual([
      { key: 'w0', wordText: 'dog', translationText: 'cachorro' },
      { key: 'w1', wordText: 'house', translationText: 'cachorro' },
    ])
    expect(hook.current.formattedScore).toBe('66,67')
    expect(hook.current.outcome).toMatchObject({
      label: 'Parcialmente correta',
      countText: '1 de 2 pares corretos',
    })
    expect(hook.current.isFull).toBe(false)
    expect(hook.current.expectedItems).toEqual([])
  })

  it('shows the expected pairs only when the key was released', () => {
    const { result: hook } = renderHook(() =>
      usePairMatchingResult({
        question: QUESTION,
        questionNumber: 3,
        result: result({
          disclosedCorrectPairs: [{ wordKey: 'w1', translationKey: 't1' }],
        }),
      }),
    )

    expect(hook.current.expectedItems).toEqual([
      { key: 'w1', wordText: 'house', translationText: 'casa' },
    ])
  })

  it('falls back to the item keys when the question is not available', () => {
    const { result: hook } = renderHook(() =>
      usePairMatchingResult({ question: undefined, questionNumber: 3, result: result() }),
    )

    expect(hook.current.submittedItems[0]).toEqual({
      key: 'w0',
      wordText: 'w0',
      translationText: 't0',
    })
  })

  it.each([
    ['full', 100, 'Resposta correta', true],
    ['incorrect', 0, 'Resposta incorreta', false],
  ] as const)('marks a %s outcome', (outcome, score, label, isFull) => {
    const { result: hook } = renderHook(() =>
      usePairMatchingResult({
        question: QUESTION,
        questionNumber: 1,
        result: result({ outcome, score }),
      }),
    )

    expect(hook.current.outcome?.label).toBe(label)
    expect(hook.current.isFull).toBe(isFull)
  })
})
