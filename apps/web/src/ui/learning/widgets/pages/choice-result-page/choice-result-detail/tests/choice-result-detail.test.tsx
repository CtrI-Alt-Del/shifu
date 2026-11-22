import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type {
  CodeQuestion,
  OrderingResultQuestion,
  ChoiceQuestion,
  CodeResultQuestion,
  HtmlCssJsQuestion,
  ChoiceResultQuestion,
  PairMatchingQuestion,
  PairMatchingResultQuestion,
  TranslationQuestion,
  TranslationResultQuestion,
} from '@/core/learning/choice-activity'

import { FillBlanksQuestionFaker } from '@/core/learning/fakers'

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
const CODE_QUESTION: CodeQuestion = {
  key: 'code-question-1',
  kind: 'javascript_stdin',
  prompt: 'Leia a entrada e imprima o dobro.',
  initialFiles: [{ path: 'main.js', content: '', editable: true }],
  entrypoint: 'main.js',
  editablePaths: ['main.js'],
  fixedDependencies: [],
  permittedCommands: [],
  criteria: [{ key: 'input-handling', name: 'Leitura da entrada', weightPercentage: 60 }],
}
const HTML_QUESTION: HtmlCssJsQuestion = {
  key: 'html-question-1',
  kind: 'html_css_js',
  prompt: 'Crie uma página semântica.',
  initialFiles: [{ path: 'index.html', content: '', editable: true }],
  entrypoint: 'index.html',
  editablePaths: ['index.html'],
  fixedDependencies: [{ name: 'vite', version: '7.0.0' }],
  permittedCommands: [],
  criteria: [{ key: 'semantic', name: 'HTML semântico', weightPercentage: 100 }],
}
const TRANSLATION_QUESTION: TranslationQuestion = {
  key: 'translation-question-1',
  kind: 'translation',
  prompt: 'Traduza o texto a seguir.',
  sourceLanguage: 'pt-BR',
  targetLanguage: 'en-US',
  sourceText: 'Bom dia',
  criteria: [
    { key: 'semantic_preservation', name: 'Preservação semântica', weightPercentage: 70 },
    { key: 'grammatical_adequacy', name: 'Adequação gramatical', weightPercentage: 30 },
  ],
}

describe('ChoiceResultDetail', () => {
  afterEach(cleanup)

  it.each([undefined, []])(
    'keeps an incorrect submitted order private until accepted sequences are disclosed (%s)',
    (acceptedOrders) => {
      const result: OrderingResultQuestion = {
        key: 'ordering-history',
        kind: 'ordering',
        prompt: 'Organize o preparo.',
        steps: [
          { key: 'wash', text: 'Lavar os legumes' },
          { key: 'cut', text: 'Cortar os legumes' },
          { key: 'cook', text: 'Cozinhar os legumes' },
        ],
        submittedStepKeys: ['cook', 'wash', 'cut'],
        score: 0,
        isCorrect: false,
        explanation: 'Revise a sequência do preparo.',
        acceptedOrders,
      }
      render(
        <ChoiceResultDetail question={undefined} questionNumber={2} result={result} />,
      )
      const submittedOrder = screen.getByRole('region', {
        name: 'Sua ordem na questão 2',
        hidden: true,
      })
      expect(submittedOrder).not.toBeVisible()
      fireEvent.click(screen.getByText('Questão 2 · ordenação · incorreta'))

      expect(screen.getByLabelText('Nota 0 de 100')).toBeVisible()
      expect(submittedOrder).toBeVisible()
      const rows = within(submittedOrder).getAllByRole('listitem')
      expect(rows[0]).toHaveTextContent('Cozinhar os legumes')
      expect(rows[1]).toHaveTextContent('Lavar os legumes')
      expect(rows[2]).toHaveTextContent('Cortar os legumes')
      expect(screen.getByText('Revise a sequência do preparo.')).toBeVisible()
      expect(screen.getByText('Sua ordem · somente leitura')).toBeVisible()
      expect(screen.queryByText('Sequências aceitas')).not.toBeInTheDocument()
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
    },
  )

  it('shows the historical correct order and every sequence explicitly released by Learning', () => {
    const result: OrderingResultQuestion = {
      key: 'ordering-history',
      kind: 'ordering',
      prompt: 'Prepare a refeição.',
      steps: [
        { key: 'wash', text: 'Lavar' },
        { key: 'cut', text: 'Cortar' },
        { key: 'cook', text: 'Cozinhar' },
      ],
      submittedStepKeys: ['wash', 'cut', 'cook'],
      score: 100,
      isCorrect: true,
      explanation: 'Sequência concluída corretamente.',
      acceptedOrders: [
        ['wash', 'cut', 'cook'],
        ['cut', 'wash', 'cook'],
      ],
    }
    render(<ChoiceResultDetail question={undefined} questionNumber={1} result={result} />)
    fireEvent.click(screen.getByText('Questão 1 · ordenação · correta'))

    expect(screen.getByLabelText('Nota 100 de 100')).toBeVisible()
    const accepted = screen.getByRole('region', { name: 'Ordens aceitas da questão 1' })
    expect(accepted).toBeVisible()
    const orders = within(accepted).getAllByRole('list')
    expect(orders).toHaveLength(2)
    expect(within(orders[0]).getAllByRole('listitem')[0]).toHaveTextContent('Lavar')
    expect(within(orders[1]).getAllByRole('listitem')[0]).toHaveTextContent('Cortar')
    expect(screen.getByText('Sequência concluída corretamente.')).toBeVisible()
  })

  it('labels unavailable historical steps without exposing their private identifiers', () => {
    const result: OrderingResultQuestion = {
      key: 'ordering-history',
      kind: 'ordering',
      prompt: 'Prepare a refeição.',
      steps: [{ key: 'known', text: 'Etapa preservada' }],
      submittedStepKeys: ['private-removed-step'],
      score: 0,
      isCorrect: false,
      explanation: 'Conteúdo histórico parcialmente indisponível.',
      acceptedOrders: [['private-accepted-step']],
    }
    render(<ChoiceResultDetail question={undefined} questionNumber={3} result={result} />)
    fireEvent.click(screen.getByText('Questão 3 · ordenação · incorreta'))

    expect(screen.getAllByText('Etapa indisponível')).toHaveLength(2)
    expect(screen.queryByText('private-removed-step')).not.toBeInTheDocument()
    expect(screen.queryByText('private-accepted-step')).not.toBeInTheDocument()
  })

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
    fireEvent.click(screen.getByText(/Questão 1 · escolha única/))

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
    fireEvent.click(screen.getByText(/Questão 1 · escolha única/))

    expect(screen.getByLabelText('Nota 0 de 100')).toBeVisible()
    expect(screen.getByText('5')).toBeVisible()
    expect(
      within(screen.getByLabelText('Alternativas visíveis da questão 1')).getByText('0'),
    ).toBeVisible()
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
    fireEvent.click(screen.getByText(/Questão 1 · incorreta/))

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
    fireEvent.click(screen.getByText(/Questão 1 · escolha única/))

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
    fireEvent.click(screen.getByText(/Questão 1 · escolha única/))

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

  it('keeps submitted code collapsed and reveals read-only files and rubric on demand', () => {
    const result: CodeResultQuestion = {
      key: 'code-question-1',
      kind: 'javascript_stdin',
      prompt: 'Leia a entrada e imprima o dobro.',
      score: 75,
      submittedFiles: [{ path: 'main.js', content: 'console.log(Number(input) * 2)' }],
      criterionResults: [
        {
          key: 'input-handling',
          weightPercentage: 60,
          level: 75,
          commentId: 'comment-1',
          comment: 'Lê a entrada corretamente.',
        },
      ],
      conceptObservations: [
        { conceptId: 'stdin', level: 75, observationId: 'observation-1' },
      ],
    }

    render(
      <ChoiceResultDetail question={CODE_QUESTION} questionNumber={2} result={result} />,
    )

    expect(screen.getByText(/Questão 2 · JavaScript · entrada padrão/)).toHaveClass(
      'text-sm',
    )
    expect(
      screen.getByText(/Questão 2 · JavaScript · entrada padrão/).parentElement,
    ).toHaveClass('flex-wrap')
    expect(
      screen.getByText(/Questão 2 · JavaScript · entrada padrão/).closest('summary'),
    ).toHaveClass('flex-col')
    expect(screen.getByLabelText('Nota 75 de 100')).toBeVisible()
    expect(screen.queryByText('console.log(Number(input) * 2)')).not.toBeVisible()
    expect(screen.queryByText('Rubrica da questão')).not.toBeVisible()
    expect(screen.queryByText('Terminal')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText(/Questão 2 · JavaScript · entrada padrão/))

    expect(screen.getByText('console.log(Number(input) * 2)')).toBeVisible()
    expect(screen.getByText('Somente leitura')).toBeVisible()
    expect(screen.getByText('Rubrica da questão')).toBeVisible()
    expect(screen.getByText('Leitura da entrada · peso 60% · nível 75')).toBeVisible()
    expect(screen.getByText('Lê a entrada corretamente.')).toBeVisible()
    expect(screen.getByText('Evidências de Conceito')).toBeVisible()
  })
  it('reveals the saved React files and rubric without running the project', () => {
    const question = {
      ...CODE_QUESTION,
      kind: 'react' as const,
      additionalFilePolicy: null,
    }
    const result: CodeResultQuestion = {
      key: question.key,
      kind: 'react',
      prompt: 'Tela React histórica',
      score: 50,
      submittedFiles: [
        { path: 'src/App.tsx', content: 'saved React source' },
        { path: 'src/extra.css', content: 'saved styles' },
      ],
      criterionResults: [
        {
          key: 'input-handling',
          weightPercentage: 60,
          level: 50,
          commentId: 'partial',
          comment: 'Comportamento parcial.',
        },
      ],
      conceptObservations: [],
    }
    render(<ChoiceResultDetail question={question} questionNumber={3} result={result} />)
    fireEvent.click(screen.getByText(/Questão 3 · React/))
    expect(screen.getByText('saved React source')).toBeVisible()
    expect(screen.getByText('saved styles')).toBeVisible()
    expect(screen.getByText('Somente leitura')).toBeVisible()
    expect(screen.getByText('Leitura da entrada · peso 60% · nível 50')).toBeVisible()
    expect(
      screen.queryByRole('button', { name: /Executar|Avaliar/ }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByTitle('Prévia isolada da aplicação React'),
    ).not.toBeInTheDocument()
  })

  it('renders HTML/CSS/JavaScript history as read-only files and rubric', () => {
    const result: CodeResultQuestion = {
      key: HTML_QUESTION.key,
      kind: 'html_css_js',
      prompt: HTML_QUESTION.prompt,
      score: 100,
      submittedFiles: [{ path: 'index.html', content: '<main>histórico</main>' }],
      criterionResults: [
        {
          key: 'semantic',
          weightPercentage: 100,
          level: 100,
          commentId: 'semantic-complete',
          comment: 'Estrutura semântica correta.',
        },
      ],
      conceptObservations: [],
    }
    render(
      <ChoiceResultDetail question={HTML_QUESTION} questionNumber={4} result={result} />,
    )

    expect(screen.getByText(/Questão 4 · HTML, CSS e JavaScript/)).toBeVisible()
    fireEvent.click(screen.getByText(/Questão 4 · HTML, CSS e JavaScript/))
    expect(screen.getByText('<main>histórico</main>')).toBeVisible()
    expect(screen.getByText('Somente leitura')).toBeVisible()
    expect(screen.getByText('HTML semântico · peso 100% · nível 100')).toBeVisible()
    expect(screen.getByText('Estrutura semântica correta.')).toBeVisible()
    expect(
      screen.queryByRole('button', { name: /Executar|Avaliar/ }),
    ).not.toBeInTheDocument()
    expect(screen.queryByTitle('Prévia isolada da página')).not.toBeInTheDocument()
  })

  it('shows integrated immutable frontend API and additional files from the persisted result without practice', () => {
    const result: CodeResultQuestion = {
      key: 'integrated',
      kind: 'react_fastify',
      prompt: 'Projeto original',
      score: 100,
      submittedFiles: [
        { path: 'src/App.tsx', content: 'original frontend' },
        { path: 'server.js', content: 'original API' },
        { path: 'routes/tasks.js', content: 'additional route' },
      ],
      criterionResults: [
        {
          key: 'integration',
          weightPercentage: 100,
          level: 100,
          commentId: 'correct',
          comment: 'Integração correta',
        },
      ],
      conceptObservations: [],
    }
    render(<ChoiceResultDetail question={undefined} questionNumber={1} result={result} />)
    fireEvent.click(screen.getByText(/Questão 1 · React \+ Fastify/))
    expect(screen.getByText('original frontend')).toBeVisible()
    expect(screen.getByText('original API')).toBeVisible()
    expect(screen.getByText('additional route')).toBeVisible()
    expect(screen.getByText('Somente leitura')).toBeVisible()
    expect(screen.getByText('Integração correta')).toBeVisible()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(screen.queryByTitle('Prévia isolada React + Fastify')).not.toBeInTheDocument()
  })
  describe('with a fill-in-the-blank result', () => {
    const question = FillBlanksQuestionFaker.fake()

    function open(result = FillBlanksQuestionFaker.fakeResult()) {
      const view = render(
        <ChoiceResultDetail question={question} questionNumber={2} result={result} />,
      )
      fireEvent.click(screen.getByText(/Questão 2 · lacunas/))
      return view
    }

    it('shows the submitted fill read-only with the score, count, label and explanation', () => {
      const { container } = open()

      expect(screen.getByText(/Questão 2 · lacunas · Parcialmente correta/)).toBeVisible()
      expect(screen.getByLabelText('Nota 66,67 de 100')).toBeVisible()
      expect(screen.getByText('Somente leitura')).toBeVisible()
      expect(screen.getByText('2 de 3 lacunas corretas')).toBeVisible()
      expect(screen.getByText('Quase lá. Revise a forma do verbo.')).toBeVisible()
      const fill = container.querySelector('p.whitespace-pre-wrap.rounded-md')
      expect(fill).toHaveTextContent(/She\s*Lacuna 1:\s*goes\s*to school and/)
      expect(fill).toHaveTextContent(/Lacuna 2:\s*go\s*her homework every/)
      expect(fill?.querySelectorAll('[lang="en"]').length).toBeGreaterThan(0)
    })

    it('never shows the expected fill while the answers are protected', () => {
      open()

      expect(screen.queryByText('Preenchimento esperado')).toBeNull()
      expect(screen.queryByText(/ ou /)).toBeNull()
    })

    it('shows the expected fill, with accepted alternatives, once it is released', () => {
      open(
        FillBlanksQuestionFaker.fakeResult({
          expectedBlanks: [
            { blankKey: 'b1', acceptedWords: ['goes', 'walks'] },
            { blankKey: 'b2', acceptedWords: ['does'] },
            { blankKey: 'b3', acceptedWords: ['day'] },
          ],
        }),
      )

      expect(
        screen.getByRole('heading', { name: 'Preenchimento esperado' }),
      ).toBeVisible()
      const expected = within(
        screen.getByRole('region', { name: 'Preenchimento esperado' }),
      )
      expect(expected.getByText('goes ou walks')).toBeVisible()
      expect(expected.getByText('does')).toBeVisible()
      expect(expected.getByText('day')).toBeVisible()
    })

    it.each([
      [100, true, 3, 'Resposta correta'],
      [66.67, false, 2, 'Parcialmente correta'],
      [0, false, 0, 'Resposta incorreta'],
    ])(
      'labels a %s score as %s with text and an icon',
      (score, isCorrect, correctBlankCount, label) => {
        const { container } = open(
          FillBlanksQuestionFaker.fakeResult({ score, isCorrect, correctBlankCount }),
        )

        expect(
          screen.getByText(new RegExp(`Questão 2 · lacunas · ${label}`)),
        ).toBeVisible()
        expect(container.querySelector('summary svg')).not.toBeNull()
        expect(
          screen.getByText(`${correctBlankCount} de 3 lacunas corretas`),
        ).toBeVisible()
      },
    )

    it('shows a dash for a blank whose word is missing from the saved bank', () => {
      open(
        FillBlanksQuestionFaker.fakeResult({
          placements: [{ blankKey: 'b1', wordKey: 'unknown' }],
        }),
      )

      expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    })

    it('uses the singular count text for a one-blank question', () => {
      open(FillBlanksQuestionFaker.fakeResult({ blankCount: 1, correctBlankCount: 1 }))

      expect(screen.getByText('1 de 1 lacuna correta')).toBeVisible()
    })
  })

  it.each([
    [100, 'Resposta correta'],
    [75, 'Parcialmente correta'],
    [0, 'Resposta incorreta'],
  ])('labels a translation result scoring %d as "%s"', (score, label) => {
    const result: TranslationResultQuestion = {
      key: TRANSLATION_QUESTION.key,
      kind: 'translation',
      prompt: TRANSLATION_QUESTION.prompt,
      score,
      submittedText: 'Good morning',
      criterionResults: [
        {
          key: 'semantic_preservation',
          weightPercentage: 70,
          level: score,
          commentId: 'comment-1',
          comment: 'Feedback da tradução.',
        },
      ],
      conceptObservations: [],
    }
    render(
      <ChoiceResultDetail
        question={TRANSLATION_QUESTION}
        questionNumber={5}
        result={result}
      />,
    )

    expect(screen.getByText(new RegExp(`Questão 5 · Tradução · ${label}`))).toBeVisible()
    fireEvent.click(screen.getByText(new RegExp(`Questão 5 · Tradução · ${label}`)))
    expect(screen.getByLabelText(`Nota ${score} de 100`)).toBeVisible()
    expect(screen.getByText('Good morning')).toBeVisible()
    expect(
      screen.getByText(`Preservação semântica · peso 70% · nível ${score}`),
    ).toBeVisible()
    expect(screen.getByText('Feedback da tradução.')).toBeVisible()
    expect(screen.queryByText('Bom dia')).not.toBeInTheDocument()
  })

  it('renders no score and no label while the translation evaluation is pending', () => {
    const result: TranslationResultQuestion = {
      key: TRANSLATION_QUESTION.key,
      kind: 'translation',
      prompt: TRANSLATION_QUESTION.prompt,
      score: null,
      submittedText: 'Good morning',
      criterionResults: [],
      conceptObservations: [],
    }
    render(
      <ChoiceResultDetail
        question={TRANSLATION_QUESTION}
        questionNumber={5}
        result={result}
      />,
    )

    expect(screen.getByText(/Questão 5 · Tradução$/)).toBeVisible()
    expect(screen.getByLabelText('Nota — de 100')).toBeVisible()
  })

  describe('pair matching', () => {
    const PAIR_QUESTION: PairMatchingQuestion = {
      key: 'pairs-1',
      kind: 'pair_matching',
      prompt: 'Associe as palavras.',
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
    const result = (
      overrides: Partial<PairMatchingResultQuestion>,
    ): PairMatchingResultQuestion => ({
      key: 'pairs-1',
      kind: 'pair_matching',
      prompt: 'Associe as palavras.',
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
    })

    it.each([
      ['full', 100, 'Resposta correta'],
      ['partial', 50, 'Parcialmente correta'],
      ['incorrect', 0, 'Resposta incorreta'],
    ] as const)(
      'labels a %s outcome with text, count and grade',
      (outcome, score, label) => {
        render(
          <ChoiceResultDetail
            question={PAIR_QUESTION}
            questionNumber={3}
            result={result({ outcome, score })}
          />,
        )

        expect(
          screen.getByText(new RegExp(`Questão 3 · Associação · ${label}`)),
        ).toBeVisible()
        expect(screen.getByLabelText(`Nota ${score} de 100`)).toBeVisible()
        expect(screen.getByText('Alguns pares estão corretos.')).toBeInTheDocument()
      },
    )

    it('shows the submitted pairs and hides the expected pairs until released', () => {
      render(
        <ChoiceResultDetail
          question={PAIR_QUESTION}
          questionNumber={3}
          result={result({})}
        />,
      )

      const submitted = screen.getByRole('list', { name: 'Pares enviados' })
      expect(within(submitted).getAllByRole('listitem')).toHaveLength(2)
      expect(within(submitted).getByText('dog — cachorro')).toBeInTheDocument()
      expect(screen.queryByText('Pares esperados')).not.toBeInTheDocument()
    })

    it('shows the expected pairs when the key was released', () => {
      render(
        <ChoiceResultDetail
          question={PAIR_QUESTION}
          questionNumber={3}
          result={result({
            disclosedCorrectPairs: [
              { wordKey: 'w0', translationKey: 't0' },
              { wordKey: 'w1', translationKey: 't1' },
            ],
          })}
        />,
      )

      const expected = screen.getByRole('list', { name: 'Pares esperados' })
      expect(within(expected).getByText('house — casa')).toBeInTheDocument()
    })
  })
})
