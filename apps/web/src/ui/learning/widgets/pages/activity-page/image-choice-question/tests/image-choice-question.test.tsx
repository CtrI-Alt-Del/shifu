import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ImageChoiceQuestion as ImageChoiceQuestionData } from '@/core/learning/choice-activity'

import { ImageChoiceQuestion, type ImageChoiceQuestionProps } from '..'

vi.mock('@/ui/shared/hooks/use-reduced-motion-preference', () => ({
  useReducedMotionPreference: vi.fn(() => ({ prefersReducedMotion: true })),
}))

const QUESTION: ImageChoiceQuestionData = {
  key: 'image-1',
  kind: 'image_choice',
  prompt: 'Qual destas cebolas está caramelizada?',
  options: [
    {
      key: 'opt-1',
      imagePath: '/curriculum/images/2d165276ed215938.webp',
      description: 'Fatias brancas e firmes.',
    },
    {
      key: 'opt-2',
      imagePath: '/curriculum/images/51de9b1cc23dd653.webp',
      description: 'Fatias claras e translúcidas.',
    },
    {
      key: 'opt-3',
      imagePath: '/curriculum/images/5c8a6a6b47848a6f.webp',
      description: 'Tiras marrons e macias.',
    },
  ],
}

function renderQuestion(overrides: Partial<ImageChoiceQuestionProps> = {}) {
  const props: ImageChoiceQuestionProps = {
    question: QUESTION,
    questionNumber: 2,
    totalQuestions: 3,
    selectedOptionKey: null,
    feedback: null,
    onSelectOption: vi.fn(),
    ...overrides,
  }
  render(<ImageChoiceQuestion {...props} />)
  return props
}

describe('ImageChoiceQuestion', () => {
  beforeEach(() => {
    vi.stubGlobal('matchMedia', () => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }))
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('shows the position, context and prompt above a labeled group of images', () => {
    renderQuestion({ activityTitle: 'Ponto de cocção', difficulty: 'easy' })

    expect(screen.getByText('Questão 2 de 3')).toBeVisible()
    expect(screen.getByText('escolha uma imagem')).toBeVisible()
    expect(
      screen.getByRole('heading', { name: 'Qual destas cebolas está caramelizada?' }),
    ).toBeVisible()
    expect(
      screen.getByRole('radiogroup', { name: 'Qual destas cebolas está caramelizada?' }),
    ).toBeVisible()
    expect(screen.getAllByRole('radio')).toHaveLength(3)
    expect(
      screen.getByRole('progressbar', { name: 'Progresso da Atividade' }),
    ).toBeVisible()
  })

  it('selects an image by click and moves the choice with the arrow keys', async () => {
    const user = userEvent.setup()
    const { onSelectOption } = renderQuestion({ selectedOptionKey: 'opt-1' })

    expect(screen.getByRole('radio', { name: 'Opção 1' })).toBeChecked()
    await user.click(screen.getByRole('radio', { name: 'Opção 2' }))
    expect(onSelectOption).toHaveBeenLastCalledWith('opt-2')
    await user.keyboard('{ArrowRight}')
    expect(onSelectOption).toHaveBeenLastCalledWith('opt-3')
  })

  it('locks the group while the page disables the question', () => {
    renderQuestion({ disabled: true, selectedOptionKey: 'opt-1' })

    for (const radio of screen.getAllByRole('radio')) expect(radio).toBeDisabled()
  })

  it('marks only the chosen image as wrong after an incorrect verification', () => {
    renderQuestion({
      selectedOptionKey: 'opt-2',
      disabled: true,
      feedback: { status: 'conclusive', score: 0, isCorrect: false },
    })

    expect(
      screen.getByRole('radio', { name: 'Opção 2' }).closest('label'),
    ).toHaveAttribute('data-tone', 'incorrect')
    expect(
      screen.getByRole('radio', { name: 'Opção 3' }).closest('label'),
    ).toHaveAttribute('data-tone', 'dimmed')
    expect(screen.getAllByText('Sua resposta')).toHaveLength(1)
    expect(screen.queryByText('Resposta correta')).not.toBeInTheDocument()
  })

  it('marks the chosen image as right after a correct verification', () => {
    renderQuestion({
      selectedOptionKey: 'opt-3',
      disabled: true,
      feedback: { status: 'conclusive', score: 100, isCorrect: true },
    })

    expect(
      screen.getByRole('radio', { name: 'Opção 3' }).closest('label'),
    ).toHaveAttribute('data-tone', 'correct')
  })

  it('keeps the choice open while a verification is inconclusive', () => {
    renderQuestion({
      selectedOptionKey: 'opt-2',
      feedback: { status: 'inconclusive', score: null },
    })

    expect(
      screen.getByRole('radio', { name: 'Opção 2' }).closest('label'),
    ).toHaveAttribute('data-tone', 'selected')
  })
})
