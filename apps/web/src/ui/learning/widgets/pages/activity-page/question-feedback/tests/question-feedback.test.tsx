import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  PairMatchingAnswer,
  PairMatchingQuestion,
  PreliminaryQuestionResult,
} from '@/core/learning/choice-activity'

import { QuestionFeedback } from '..'
import { useQuestionFeedback } from '../use-question-feedback'

vi.mock('../use-question-feedback', () => ({ useQuestionFeedback: vi.fn() }))

const useQuestionFeedbackMock = vi.mocked(useQuestionFeedback)

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
const ANSWER: PairMatchingAnswer = {
  kind: 'pair_matching',
  questionKey: 'pairs-1',
  pairs: [
    { wordKey: 'w0', translationKey: 't0' },
    { wordKey: 'w1', translationKey: 't0' },
  ],
}

function renderFeedback(feedback: PreliminaryQuestionResult) {
  render(
    <QuestionFeedback feedback={feedback} frozenAnswer={ANSWER} question={QUESTION} />,
  )
}

describe('QuestionFeedback for pair matching', () => {
  beforeEach(() => {
    useQuestionFeedbackMock.mockReturnValue({
      feedbackElementRef: { current: null },
      fillBlanksOutcome: null,
    })
  })

  afterEach(cleanup)

  it.each([
    ['full', 100, 'Resposta correta'],
    ['partial', 50, 'Parcialmente correta'],
    ['incorrect', 0, 'Resposta incorreta'],
  ] as const)(
    'shows the %s outcome as text with the pair count',
    (outcome, score, label) => {
      renderFeedback({
        status: 'conclusive',
        score,
        outcome,
        correctPairCount: 1,
        totalPairCount: 2,
        explanation: 'Explicação predefinida.',
      })

      expect(screen.getByText(label)).toBeVisible()
      expect(screen.getByText(/1 de 2 pares corretos\./)).toBeVisible()
      expect(screen.getByText('Explicação predefinida.')).toBeVisible()
    },
  )

  it('lists the submitted pairs without marking them and never shows expected pairs', () => {
    renderFeedback({
      status: 'conclusive',
      score: 0,
      outcome: 'incorrect',
      correctPairCount: 0,
      totalPairCount: 2,
      submittedPairs: ANSWER.pairs,
    })

    const submitted = screen.getByRole('list', { name: 'Pares enviados' })
    expect(within(submitted).getAllByRole('listitem')).toHaveLength(2)
    expect(within(submitted).getByText(/dog\s+—\s+cachorro/)).toBeInTheDocument()
    expect(screen.queryByText(/esperad/i)).not.toBeInTheDocument()
  })

  it('falls back to the item key when a submitted key is unknown', () => {
    renderFeedback({
      status: 'conclusive',
      score: 0,
      outcome: 'incorrect',
      submittedPairs: [{ wordKey: 'ghost', translationKey: 't0' }],
    })

    expect(screen.getByText(/ghost\s+—\s+cachorro/)).toBeInTheDocument()
  })
})
