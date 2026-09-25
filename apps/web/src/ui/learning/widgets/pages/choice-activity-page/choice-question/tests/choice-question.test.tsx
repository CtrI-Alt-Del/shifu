import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ChoiceQuestionProps } from '../../use-choice-activity-page'
import { ChoiceQuestion } from '..'

const SINGLE_QUESTION: ChoiceQuestionProps['question'] = {
  key: 'single-1',
  kind: 'single_choice',
  prompt: 'Qual é o valor de total ao final?',
  options: [
    { key: 'a', text: '1' },
    { key: 'b', text: '5' },
  ],
}

const MULTIPLE_QUESTION: ChoiceQuestionProps['question'] = {
  key: 'multiple-1',
  kind: 'multiple_selection',
  prompt: 'Quais afirmações são verdadeiras?',
  options: [
    { key: 'a', text: 'A primeira afirmação' },
    { key: 'b', text: 'A segunda afirmação' },
  ],
}

describe('ChoiceQuestion', () => {
  afterEach(cleanup)

  it('renders a labeled single-choice group and supports native keyboard selection', async () => {
    const user = userEvent.setup()
    const onToggleOptionMock = vi.fn()
    render(
      <ChoiceQuestion
        onToggleOption={onToggleOptionMock}
        question={SINGLE_QUESTION}
        questionNumber={2}
        selectedOptionKeys={[]}
        totalQuestions={3}
      />,
    )

    expect(
      screen.getByRole('heading', { name: 'Qual é o valor de total ao final?' }),
    ).toBeVisible()
    expect(screen.getByText('Questão 2 de 3')).toBeVisible()
    expect(
      screen.getByRole('radiogroup', { name: 'Qual é o valor de total ao final?' }),
    ).toBeVisible()
    await user.click(screen.getByRole('radio', { name: '1' }))
    expect(screen.getByRole('radio', { name: '1' })).toHaveFocus()
    await user.keyboard('{ArrowDown}')
    expect(onToggleOptionMock).toHaveBeenCalledWith('b')
  })

  it('renders independently removable multiple choices as labeled checkboxes', () => {
    const onToggleOptionMock = vi.fn()
    render(
      <ChoiceQuestion
        onToggleOption={onToggleOptionMock}
        question={MULTIPLE_QUESTION}
        questionNumber={1}
        selectedOptionKeys={['a']}
        totalQuestions={3}
      />,
    )

    expect(screen.getByRole('checkbox', { name: 'A primeira afirmação' })).toBeChecked()
    fireEvent.click(screen.getByRole('checkbox', { name: 'A primeira afirmação' }))
    expect(onToggleOptionMock).toHaveBeenCalledWith('a')
    expect(
      screen.getByRole('checkbox', { name: 'A segunda afirmação' }),
    ).not.toBeChecked()
  })

  it('renders a fenced code example in a single-choice prompt', () => {
    render(
      <ChoiceQuestion
        onToggleOption={vi.fn()}
        question={{
          ...SINGLE_QUESTION,
          prompt:
            'Considere o código:\n\n```python\nidade = 17\npode_entrar = idade >= 18\n```\n\nQual é o valor de `pode_entrar`?',
        }}
        questionNumber={1}
        selectedOptionKeys={[]}
        totalQuestions={1}
      />,
    )

    const heading = screen.getByRole('heading', { level: 2 })
    expect(heading).toHaveTextContent('pode_entrar = idade >= 18')
    expect(heading.querySelector('pre code.language-python')).toHaveTextContent(
      'idade = 17',
    )
    expect(heading.querySelector('pre .token.number')).toHaveTextContent('17')
    expect(heading.querySelector('pre .token.operator')).toHaveTextContent('=')
    expect(screen.getByRole('radiogroup')).toBeVisible()
    expect(screen.queryByText('```python')).not.toBeInTheDocument()
  })

  it('renders a multiple-selection prompt without interpreting raw HTML', () => {
    render(
      <ChoiceQuestion
        onToggleOption={vi.fn()}
        question={{
          ...MULTIPLE_QUESTION,
          prompt: 'Quais são verdadeiras? <script>bad()</script> **Selecione todas.**',
        }}
        questionNumber={1}
        selectedOptionKeys={[]}
        totalQuestions={1}
      />,
    )

    expect(screen.getByText('Selecione todas.')).toBeVisible()
    expect(screen.getByRole('group')).toBeVisible()
    expect(document.querySelector('script')).not.toBeInTheDocument()
  })
})
