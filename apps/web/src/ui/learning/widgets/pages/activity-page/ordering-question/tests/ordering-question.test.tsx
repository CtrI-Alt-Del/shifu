import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { OrderingQuestion as OrderingQuestionData } from '@/core/learning/choice-activity'

import { OrderingQuestion } from '..'

const QUESTION: OrderingQuestionData = {
  key: 'order-1',
  kind: 'ordering',
  prompt: 'Organize o preparo.',
  steps: [
    { key: 'wash', text: 'Lavar os legumes' },
    { key: 'cut', text: 'Cortar os legumes' },
    { key: 'cook', text: 'Aquecer a frigideira' },
  ],
  initialOrderedStepKeys: ['wash', 'cut', 'cook'],
  verified: null,
}

describe('OrderingQuestion', () => {
  afterEach(() => cleanup())

  it('moves a step and announces its new position', () => {
    const onOrderChangeMock = vi.fn()
    render(
      <OrderingQuestion
        onOrderChange={onOrderChangeMock}
        orderedStepKeys={QUESTION.initialOrderedStepKeys}
        question={QUESTION}
        questionNumber={1}
        totalQuestions={3}
      />,
    )

    expect(
      screen.getByRole('button', { name: 'Mover para cima: Lavar os legumes' }),
    ).toBeDisabled()
    fireEvent.click(
      screen.getByRole('button', { name: 'Mover para baixo: Lavar os legumes' }),
    )

    const steps = screen.getByRole('list', { name: 'Etapas do procedimento' })
    expect(
      within(steps)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['1Cortar os legumes', '2Lavar os legumes', '3Aquecer a frigideira'])
    expect(
      screen.getByText('Lavar os legumes agora está na posição 2 de 3.'),
    ).toBeInTheDocument()
    expect(onOrderChangeMock).toHaveBeenCalledWith(['cut', 'wash', 'cook'])
  })

  it('keeps the checked order read-only and removes movement controls', () => {
    render(
      <OrderingQuestion
        isVerified
        orderedStepKeys={['cut', 'wash', 'cook']}
        question={{
          ...QUESTION,
          verified: {
            orderedStepKeys: ['cut', 'wash', 'cook'],
            score: 0,
            isCorrect: false,
            explanation: 'Revise a ordem.',
          },
        }}
        questionNumber={1}
        totalQuestions={3}
      />,
    )

    expect(screen.getByText('Ordem verificada. Somente leitura.')).toBeVisible()
    expect(screen.queryByRole('button', { name: /Mover para/ })).not.toBeInTheDocument()
    expect(screen.getByText('Cortar os legumes').closest('li')).toHaveTextContent('1')
  })
})
