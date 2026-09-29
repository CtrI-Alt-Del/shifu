import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CodePracticeRunner } from '@/core/learning/code-practice-runner'
import { CodeQuestion } from '..'
import { useCodeQuestion, type CodeQuestionProps } from '../use-code-question'

vi.mock('../use-code-question', () => ({ useCodeQuestion: vi.fn() }))
vi.mock('@/ui/learning/widgets/components/code-editor', () => ({
  CodeEditor: () => <fieldset aria-label='Editor de código' />,
}))
vi.mock('../code-terminal', () => ({
  CodeTerminal: () => <fieldset aria-label='Terminal de prática' />,
}))
const useCodeQuestionMock = vi.mocked(useCodeQuestion)
const question: CodeQuestionProps['question'] = {
  key: 'q1',
  prompt: 'Conte vogais',
  initialFiles: [{ path: 'main.js', content: '', editable: true }],
  entrypoint: 'main.js',
  editablePaths: ['main.js'],
  fixedDependencies: [],
  permittedCommands: [],
}

describe('CodeQuestion', () => {
  afterEach(cleanup)
  beforeEach(() => {
    useCodeQuestionMock.mockClear()
    useCodeQuestionMock.mockReturnValue({
      files: [{ path: 'main.js', content: '' }],
      editablePaths: ['main.js'],
      hasAssessError: false,
      isAssessing: false,
      isFrozen: false,
      practiceStatus: 'waiting-input',
      runner: null,
      selectedPanel: 'prompt',
      selectedPath: 'main.js',
      sidebarWidth: 280,
      editorWidth: null,
      resizeValues: {
        sidebar: { minimum: 220, maximum: 500, current: 280 },
        editor: { minimum: 280, maximum: 600, current: 440 },
      },
      workspaceRef: { current: null },
      editorGridRef: { current: null },
      handleAssess: vi.fn(),
      handleFileChange: vi.fn(),
      handleSelectFile: vi.fn(),
      handleSelectPanel: vi.fn(),
      handleResizePointerDown: vi.fn(),
      handleResizePointerMove: vi.fn(),
      handleResizePointerEnd: vi.fn(),
      handleResizeKeyDown: vi.fn(),
    })
  })

  it('shows the prompt, editor, terminal, and preliminary action', () => {
    render(<CodeQuestion question={question} onAssess={vi.fn()} />)
    expect(screen.getByText('Conte vogais')).toBeVisible()
    expect(screen.getByRole('group', { name: 'Editor de código' })).toBeVisible()
    expect(screen.getByRole('group', { name: 'Terminal de prática' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
  })

  it('renders inline and fenced Markdown in a code question prompt', () => {
    render(
      <CodeQuestion
        question={{
          ...question,
          prompt:
            'Complete `classificarNumero`:\n\n```javascript\nconst numero = 0;\nconsole.log(numero);\n```',
        }}
      />,
    )

    const prompt = screen.getByRole('heading', { name: /Complete classificarNumero:/ })
    expect(prompt.querySelector('p code')).toHaveTextContent('classificarNumero')
    expect(prompt.querySelector('pre code')).toHaveTextContent('const numero = 0;')
    expect(prompt.querySelector('pre .token.keyword')).toHaveTextContent('const')
    expect(prompt).not.toHaveTextContent('`classificarNumero`')
  })

  it('passes the injected runner factory through the widget boundary', () => {
    const runnerFactory = vi.fn<() => CodePracticeRunner>()
    render(<CodeQuestion question={question} runnerFactory={runnerFactory} />)
    expect(useCodeQuestionMock).toHaveBeenCalledWith(
      expect.objectContaining({ runnerFactory }),
    )
  })

  it('keeps code practice available without exposing preliminary evaluation in diagnosis', () => {
    render(<CodeQuestion question={question} isDiagnostic onFilesChange={vi.fn()} />)

    expect(screen.queryByText('Questão 1 de 1')).not.toBeInTheDocument()
    expect(
      screen.queryByRole('progressbar', { name: 'Progresso da Atividade' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Editor de código' })).toBeVisible()
    expect(screen.getByRole('group', { name: 'Terminal de prática' })).toBeVisible()
    expect(screen.getByText(/não mostram o resultado do diagnóstico/i)).toBeVisible()
    expect(
      screen.queryByRole('button', { name: 'Avaliar questão' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText('Como será avaliado')).not.toBeInTheDocument()
  })

  it('renders named desktop separators with values and keyboard controls', () => {
    render(<CodeQuestion question={question} />)
    const sidebar = screen.getByRole('separator', {
      name: 'Redimensionar enunciado e editor',
    })
    const editor = screen.getByRole('separator', {
      name: 'Redimensionar editor e terminal',
    })
    expect(sidebar).toHaveAttribute('aria-orientation', 'vertical')
    expect(sidebar).toHaveAttribute('aria-valuenow', '280')
    expect(editor).toHaveAttribute('aria-valuenow', '440')
    fireEvent.keyDown(editor, { key: 'ArrowRight' })
    expect(
      useCodeQuestionMock.mock.results.at(-1)?.value.handleResizeKeyDown,
    ).toHaveBeenCalled()
  })

  it('freezes the assessment action and reports recoverable failure', () => {
    useCodeQuestionMock.mockReturnValue({
      files: [{ path: 'main.js', content: '' }],
      editablePaths: ['main.js'],
      hasAssessError: true,
      isAssessing: true,
      isFrozen: true,
      practiceStatus: 'unavailable',
      runner: null,
      selectedPanel: 'prompt',
      selectedPath: 'main.js',
      sidebarWidth: 280,
      editorWidth: null,
      resizeValues: {
        sidebar: { minimum: 220, maximum: 500, current: 280 },
        editor: { minimum: 280, maximum: 600, current: 440 },
      },
      workspaceRef: { current: null },
      editorGridRef: { current: null },
      handleAssess: vi.fn(),
      handleFileChange: vi.fn(),
      handleSelectFile: vi.fn(),
      handleSelectPanel: vi.fn(),
      handleResizePointerDown: vi.fn(),
      handleResizePointerMove: vi.fn(),
      handleResizePointerEnd: vi.fn(),
      handleResizeKeyDown: vi.fn(),
    })
    render(<CodeQuestion onAssess={vi.fn()} question={question} />)
    expect(screen.getByRole('button', { name: 'Avaliando questão…' })).toBeDisabled()
    expect(screen.getByRole('alert')).toHaveTextContent('Tente novamente')
    expect(
      screen.queryByText('A saída da prática não altera a avaliação.'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText('Prática indisponível. Você ainda pode editar e avaliar.'),
    ).not.toBeInTheDocument()
  })

  it('hides practice in read only feedback', () => {
    render(<CodeQuestion question={question} readOnly />)
    expect(
      screen.queryByRole('group', { name: 'Terminal de prática' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Avaliar questão' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('separator')).not.toBeInTheDocument()
  })
})
