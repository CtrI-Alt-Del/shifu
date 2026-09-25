import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type {
  ChoiceQuestion,
  ChoiceResultQuestion,
} from '@/core/learning/choice-activity'

import { ChoiceResultDetail } from '..'

const QUESTION: ChoiceQuestion = {
  key: 'question-1',
  kind: 'single_choice',
  prompt: 'Qual é o valor final?',
  options: [
    { key: 'option-correct', text: '5' },
    { key: 'option-selected', text: '0' },
    { key: 'option-hidden', text: '10' },
  ],
}

describe('ChoiceResultDetail', () => {
  afterEach(cleanup)

  it('shows only the submitted selection and safe feedback when disclosure is protected', () => {
    const result: ChoiceResultQuestion = {
      key: 'question-1',
      prompt: QUESTION.prompt,
      submittedOptionKeys: ['option-selected'],
      score: 0,
      isCorrect: false,
      explanation: 'Revise como a repetição atualiza o total.',
    }
    render(<ChoiceResultDetail question={QUESTION} questionNumber={1} result={result} />)

    expect(screen.getByLabelText('Nota 0 de 100')).toBeVisible()
    expect(screen.getByText('Revise como a repetição atualiza o total.')).toBeVisible()
    expect(screen.queryByText('5')).not.toBeInTheDocument()
    expect(screen.queryByText('10')).not.toBeInTheDocument()
    expect(screen.queryByText('option-correct')).not.toBeInTheDocument()
  })

  it('shows explicitly released correct options and omits keys missing from the safe Activity', () => {
    const result: ChoiceResultQuestion = {
      key: 'question-1',
      prompt: QUESTION.prompt,
      submittedOptionKeys: ['option-selected'],
      correctOptionKeys: ['option-correct', 'unknown-key'],
      score: 0,
      isCorrect: false,
      explanation: 'Agora você pode comparar as alternativas.',
    }
    render(<ChoiceResultDetail question={QUESTION} questionNumber={1} result={result} />)

    expect(screen.getByLabelText('Nota 0 de 100')).toBeVisible()
    expect(screen.getByText('5')).toBeVisible()
    expect(screen.getByText('0', { selector: 'span' })).toBeVisible()
    expect(screen.queryByText('unknown-key')).not.toBeInTheDocument()
    expect(screen.queryByText('10')).not.toBeInTheDocument()
  })

  it('does not reveal option identifiers when an option is absent from the safe Activity', () => {
    const result: ChoiceResultQuestion = {
      key: 'question-1',
      prompt: QUESTION.prompt,
      submittedOptionKeys: ['private-option-key'],
      score: 0,
      isCorrect: false,
      explanation: 'Feedback seguro.',
    }
    render(<ChoiceResultDetail question={undefined} questionNumber={1} result={result} />)

    expect(screen.getByText('Sua seleção não está disponível.')).toBeVisible()
    expect(screen.queryByText('private-option-key')).not.toBeInTheDocument()
  })

  it('formats persisted integer and fractional question scores compactly', () => {
    const integerResult: ChoiceResultQuestion = {
      key: 'question-1',
      prompt: QUESTION.prompt,
      submittedOptionKeys: ['option-selected'],
      score: '100.00' as unknown as number,
      isCorrect: true,
      explanation: 'Resposta correta.',
    }
    const { rerender } = render(
      <ChoiceResultDetail
        question={QUESTION}
        questionNumber={1}
        result={integerResult}
      />,
    )

    expect(screen.getByLabelText('Nota 100 de 100')).toBeVisible()

    const fractionalResult: ChoiceResultQuestion = {
      ...integerResult,
      score: '72.50' as unknown as number,
    }
    rerender(
      <ChoiceResultDetail
        question={QUESTION}
        questionNumber={1}
        result={fractionalResult}
      />,
    )

    expect(screen.getByLabelText('Nota 72,5 de 100')).toBeVisible()
  })

  it('renders the persisted fenced code in the result prompt', () => {
    const prompt = 'Considere:\n\n```python\nativo = True\n```\n\nQual é o valor?'
    render(
      <ChoiceResultDetail
        question={{ ...QUESTION, prompt }}
        questionNumber={1}
        result={{
          key: QUESTION.key,
          prompt,
          submittedOptionKeys: ['option-selected'],
          score: 0,
          isCorrect: false,
          explanation: 'Revise o valor.',
        }}
      />,
    )

    expect(
      screen.getByRole('heading', { level: 2 }).querySelector('pre code.language-python'),
    ).toHaveTextContent('ativo = True')
    expect(document.querySelector('pre .token.boolean')).toHaveTextContent('True')
    expect(screen.queryByText('```python')).not.toBeInTheDocument()
  })
})
