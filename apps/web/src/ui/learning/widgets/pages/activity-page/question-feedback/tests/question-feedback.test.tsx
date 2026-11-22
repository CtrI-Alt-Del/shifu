import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  ImageChoiceAnswer,
  ImageChoiceQuestion,
  PairMatchingAnswer,
  PairMatchingQuestion,
  PreliminaryQuestionResult,
} from '@/core/learning/choice-activity'

import { QuestionFeedback } from '..'
import { useQuestionFeedback } from '../use-question-feedback'
import { usePairMatchingOutcome } from '@/ui/learning/hooks/use-pair-matching-outcome'

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
    useQuestionFeedbackMock.mockImplementation(({ feedback }) => ({
      feedbackElementRef: { current: null },
      fillBlanksOutcome: null,
      pairMatchingOutcome: usePairMatchingOutcome({
        correctPairCount: feedback.correctPairCount,
        outcome: feedback.outcome,
        totalPairCount: feedback.totalPairCount,
      }),
    }))
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
      expect(screen.getByText('1 de 2 pares corretos')).toBeVisible()
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

const IMAGE_QUESTION: ImageChoiceQuestion = {
  key: 'image-1',
  kind: 'image_choice',
  prompt: 'Qual destas cebolas está caramelizada?',
  options: [
    {
      key: 'opt-1',
      imagePath: '/curriculum/images/2d165276ed215938.webp',
      description: 'Crua.',
    },
    {
      key: 'opt-2',
      imagePath: '/curriculum/images/655fecc77404ac40.webp',
      description: 'Escura.',
    },
  ],
}
const IMAGE_ANSWER: ImageChoiceAnswer = {
  kind: 'image_choice',
  questionKey: 'image-1',
  selectedOptionKeys: ['opt-2'],
}

describe('QuestionFeedback for image choice', () => {
  beforeEach(() => {
    useQuestionFeedbackMock.mockReturnValue({
      feedbackElementRef: { current: null },
      fillBlanksOutcome: null,
      pairMatchingOutcome: null,
    })
  })

  afterEach(cleanup)

  function renderImageFeedback(feedback: PreliminaryQuestionResult) {
    render(
      <QuestionFeedback
        feedback={feedback}
        frozenAnswer={IMAGE_ANSWER}
        question={IMAGE_QUESTION}
      />,
    )
  }

  it('shows the correct outcome with icon, option line, explanation and the provisional notice', () => {
    renderImageFeedback({
      status: 'conclusive',
      score: 100,
      isCorrect: true,
      optionFeedback: 'Você reconheceu a cebola caramelizada.',
      explanation: 'Ela fica marrom-âmbar e macia.',
    })

    expect(screen.getByRole('heading', { name: 'Resposta correta' })).toBeVisible()
    expect(screen.getByText('Você reconheceu a cebola caramelizada.')).toBeVisible()
    expect(screen.getByText('Ela fica marrom-âmbar e macia.')).toBeVisible()
    expect(
      screen.getByText(
        'Retorno provisório. O resultado oficial aparece ao enviar a Atividade.',
      ),
    ).toBeVisible()
    expect(screen.queryByText(/Pontuação/)).not.toBeInTheDocument()
  })

  it('shows the incorrect outcome without identifying the correct image', () => {
    renderImageFeedback({
      status: 'conclusive',
      score: 0,
      isCorrect: false,
      optionFeedback: 'Essa cebola passou do ponto e queimou.',
      explanation: 'Revise a cor e a textura.',
    })

    expect(screen.getByRole('heading', { name: 'Resposta incorreta' })).toBeVisible()
    expect(screen.getByText('Essa cebola passou do ponto e queimou.')).toBeVisible()
    expect(screen.queryByText('Resposta correta')).not.toBeInTheDocument()
    expect(screen.queryByText(/opt-1/)).not.toBeInTheDocument()
  })

  it('asks for a new verification when the result is inconclusive', () => {
    renderImageFeedback({ status: 'inconclusive', score: null })

    expect(
      screen.getByText(
        'Não foi possível concluir esta avaliação. Reavalie a mesma resposta.',
      ),
    ).toBeVisible()
    expect(screen.queryByRole('heading', { name: /Resposta/ })).not.toBeInTheDocument()
  })
})
