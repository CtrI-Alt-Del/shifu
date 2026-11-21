import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { useState } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type {
  PairMatchingPair,
  PairMatchingQuestion as PairMatchingQuestionCore,
} from '@/core/learning/choice-activity'

import { PairMatchingQuestion } from '..'

const QUESTION: PairMatchingQuestionCore = {
  key: 'pairs-1',
  kind: 'pair_matching',
  prompt: 'Associe cada palavra à sua tradução.',
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

function Harness({
  disabled = false,
  initial = [],
  onChange,
}: {
  disabled?: boolean
  initial?: readonly PairMatchingPair[]
  onChange?: (pairs: readonly PairMatchingPair[]) => void
}) {
  const [pairs, setPairs] = useState(initial)
  return (
    <PairMatchingQuestion
      disabled={disabled}
      onChange={(next) => {
        setPairs(next)
        onChange?.(next)
      }}
      pairs={pairs}
      question={QUESTION}
      questionNumber={1}
      totalQuestions={3}
    />
  )
}

describe('PairMatchingQuestion', () => {
  afterEach(cleanup)

  it('renders the prompt, languages and both lists in display order', () => {
    render(<Harness />)

    expect(
      screen.getByRole('heading', { name: 'Associe cada palavra à sua tradução.' }),
    ).toBeVisible()
    expect(screen.getByText('Idioma das palavras')).toBeVisible()
    const lists = screen.getAllByRole('list')
    expect(
      within(lists[0])
        .getAllByRole('button')
        .map((item) => item.textContent),
    ).toEqual(['dog', 'house'])
    expect(
      within(lists[1])
        .getAllByRole('button')
        .map((item) => item.textContent),
    ).toEqual(['casa', 'cachorro'])
    expect(screen.getByText('0 de 2 pares formados.')).toBeVisible()
  })

  it('forms a pair by click and shows it with text, number and icon', () => {
    const onChange = vi.fn()
    render(<Harness onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'dog' }))
    expect(screen.getByRole('button', { name: 'dog, selecionada' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    fireEvent.click(screen.getByRole('button', { name: 'cachorro' }))

    expect(onChange).toHaveBeenLastCalledWith([{ wordKey: 'w0', translationKey: 't0' }])
    expect(screen.getByRole('button', { name: 'dog, par 1 com cachorro' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'cachorro, par 1 com dog' })).toBeVisible()
    expect(
      within(screen.getByRole('list', { name: 'Pares formados' })).getByRole('listitem'),
    ).toHaveTextContent('Par 1: dog — cachorro')
    expect(screen.getByText('1 de 2 pares formados.')).toBeVisible()
  })

  it('removes a pair with its labelled control', () => {
    render(<Harness initial={[{ wordKey: 'w0', translationKey: 't0' }]} />)

    fireEvent.click(screen.getByRole('button', { name: 'Remover par 1: dog e cachorro' }))

    expect(screen.getByText('0 de 2 pares formados.')).toBeVisible()
    expect(screen.getByRole('button', { name: 'dog' })).toBeVisible()
  })

  it('announces the current step to assistive technology', () => {
    render(<Harness />)

    fireEvent.click(screen.getByRole('button', { name: 'casa' }))
    expect(screen.getByRole('status')).toHaveTextContent(
      'Selecione primeiro uma palavra.',
    )
    fireEvent.click(screen.getByRole('button', { name: 'house' }))
    expect(screen.getByRole('status')).toHaveTextContent(
      'house selecionada. Escolha a tradução.',
    )
  })

  it('clears a pending selection with Escape', () => {
    render(<Harness />)

    fireEvent.click(screen.getByRole('button', { name: 'dog' }))
    fireEvent.keyDown(screen.getByRole('button', { name: 'dog, selecionada' }), {
      key: 'Escape',
    })

    expect(screen.getByRole('button', { name: 'dog' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  it('is read-only after verification and says so in text', () => {
    render(
      <Harness
        disabled
        initial={[
          { wordKey: 'w0', translationKey: 't0' },
          { wordKey: 'w1', translationKey: 't1' },
        ]}
      />,
    )

    for (const button of screen.getAllByRole('button')) expect(button).toBeDisabled()
    expect(screen.getAllByText('Somente leitura')).toHaveLength(2)
    expect(screen.getByText(/Resposta avaliada: não é possível alterar\./)).toBeVisible()
    expect(screen.queryByRole('button', { name: /Remover par/ })).toBeNull()
  })
})
