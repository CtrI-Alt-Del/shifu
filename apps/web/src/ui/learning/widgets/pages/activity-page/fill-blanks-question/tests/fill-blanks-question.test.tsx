import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { FillBlanksPlacement } from '@/core/learning/choice-activity'
import { FillBlanksQuestionFaker } from '@/core/learning/fakers'

import { FillBlanksQuestion, type FillBlanksQuestionProps } from '..'
import { useFillBlanksQuestion } from '../use-fill-blanks-question'

vi.mock('../use-fill-blanks-question', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../use-fill-blanks-question')>()),
  useFillBlanksQuestion: vi.fn(),
}))

const useFillBlanksQuestionMock = vi.mocked(useFillBlanksQuestion)
const question = FillBlanksQuestionFaker.fake()

type HookState = ReturnType<typeof useFillBlanksQuestion>

function hookState(
  placements: readonly FillBlanksPlacement[] = [],
  overrides: Partial<HookState> = {},
): HookState {
  const placedKeys = new Set(placements.map((placement) => placement.wordKey))
  return {
    announcement: '',
    availableWords: question.bank.filter((word) => !placedKeys.has(word.key)),
    blankCount: 3,
    blankNumberByKey: new Map([
      ['b1', 1],
      ['b2', 2],
      ['b3', 3],
    ]),
    filledBlankCount: placements.length,
    placedWordKeyByBlank: new Map(
      placements.map((placement) => [placement.blankKey, placement.wordKey]),
    ),
    selectedWordKey: null,
    sensors: [],
    wordByKey: new Map(question.bank.map((word) => [word.key, word])),
    handleBlankActivate: vi.fn(),
    handleDragCancel: vi.fn(),
    handleDragEnd: vi.fn(),
    handleDragStart: vi.fn(),
    handleWordSelect: vi.fn(),
    ...overrides,
  }
}

function renderQuestion(overrides: Partial<FillBlanksQuestionProps> = {}) {
  return render(
    <FillBlanksQuestion
      activityTitle='Presente simples'
      difficulty='easy'
      onPlacementsChange={vi.fn()}
      placements={[]}
      question={question}
      questionNumber={2}
      totalQuestions={4}
      {...overrides}
    />,
  )
}

describe('FillBlanksQuestion', () => {
  beforeEach(() => {
    useFillBlanksQuestionMock.mockReturnValue(hookState())
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders the prompt, the guidance and the position in pt-BR', () => {
    renderQuestion()

    expect(
      screen.getByRole('heading', {
        name: 'Complete o texto com as palavras do banco.',
      }),
    ).toBeVisible()
    expect(screen.getByText(/Arraste uma palavra até a lacuna/)).toBeVisible()
    expect(screen.getByText('Questão 2 de 4')).toBeVisible()
    expect(screen.getByText('preencha as lacunas')).toBeVisible()
    expect(screen.getByText('0 de 3 lacunas preenchidas')).toBeVisible()
  })

  it('names every empty blank and marks the content language on its text', () => {
    const { container } = renderQuestion()

    expect(screen.getByRole('button', { name: 'Lacuna 1: vazia' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Lacuna 2: vazia' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Lacuna 3: vazia' })).toBeVisible()
    expect(container.querySelector('span[lang="en"]')?.textContent).toBe('She ')
  })

  it('lists every bank occurrence, including the repeated word, in the studied language', () => {
    renderQuestion()

    const bank = screen.getByRole('region', { name: 'Banco de palavras' })
    expect(within(bank).getAllByRole('button')).toHaveLength(6)
    expect(within(bank).getAllByRole('button', { name: 'day' })).toHaveLength(2)
    expect(within(bank).getByRole('button', { name: 'go' })).toBeVisible()
    expect(bank.querySelector('[lang="en"]')).not.toBeNull()
  })

  it('shows a selected word with text and pressed state, not only color', () => {
    useFillBlanksQuestionMock.mockReturnValue(hookState([], { selectedWordKey: 'w1' }))
    renderQuestion()

    const selected = screen.getByRole('button', { name: /goes/ })
    expect(selected).toHaveAttribute('aria-pressed', 'true')
    expect(selected).toHaveTextContent('Selecionada')
    expect(screen.getByRole('button', { name: 'walks' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  it('names a filled blank with its word, removes the word from the bank and updates the count', () => {
    useFillBlanksQuestionMock.mockReturnValue(
      hookState([{ blankKey: 'b1', wordKey: 'w1' }]),
    )
    renderQuestion()

    expect(
      screen.getByRole('button', {
        name: 'Lacuna 1: goes. Ative para remover a palavra.',
      }),
    ).toBeVisible()
    const bank = screen.getByRole('region', { name: 'Banco de palavras' })
    expect(within(bank).queryByRole('button', { name: 'goes' })).toBeNull()
    expect(screen.getByText('1 de 3 lacunas preenchidas')).toBeVisible()
  })

  it('tells the learner when every word is already in a blank', () => {
    useFillBlanksQuestionMock.mockReturnValue(hookState([], { availableWords: [] }))
    renderQuestion()

    expect(
      screen.getByText('Todas as palavras foram colocadas nas lacunas.'),
    ).toBeVisible()
  })

  it('delegates a word click and a blank click to the owning hook', () => {
    const state = hookState()
    useFillBlanksQuestionMock.mockReturnValue(state)
    renderQuestion()

    fireEvent.click(screen.getByRole('button', { name: 'walks' }))
    fireEvent.click(screen.getByRole('button', { name: 'Lacuna 2: vazia' }))

    expect(state.handleWordSelect).toHaveBeenCalledWith('w2')
    expect(state.handleBlankActivate).toHaveBeenCalledWith('b2')
  })

  it('disables every word and blank while the question is locked', () => {
    renderQuestion({ disabled: true })

    for (const button of screen.getAllByRole('button')) expect(button).toBeDisabled()
  })

  it('announces changes in a polite status region', () => {
    useFillBlanksQuestionMock.mockReturnValue(
      hookState([], { announcement: 'Palavra "goes" colocada na lacuna 1.' }),
    )
    renderQuestion()

    const region = screen
      .getAllByRole('status')
      .find((element) => element.getAttribute('aria-live') === 'polite')
    expect(region).toHaveTextContent('Palavra "goes" colocada na lacuna 1.')
  })
})
