import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { HtmlCssJsQuestion as HtmlQuestion } from '@/core/learning/choice-activity'
import type { HtmlCssJsQuestionProps } from '../use-html-css-js-question'
import type { CodeEditorProps } from '@/ui/learning/widgets/components/code-editor'
import { HtmlCssJsQuestion } from '..'
import { useHtmlCssJsQuestion } from '../use-html-css-js-question'

vi.mock('../use-html-css-js-question', () => ({ useHtmlCssJsQuestion: vi.fn() }))
vi.mock('@/ui/learning/widgets/components/code-editor', () => ({
  CodeEditor: ({ files, selectedPath, readOnly, onFileChange }: CodeEditorProps) => {
    const selected = files.find((file) => file.path === selectedPath) ?? files[0]
    return (
      <textarea
        aria-label='Editor de arquivo'
        readOnly={readOnly}
        value={selected?.content ?? ''}
        onChange={(event) =>
          selected && onFileChange?.(selected.path, event.target.value)
        }
      />
    )
  },
}))
vi.mock('@/ui/learning/widgets/components/code-file-tree', () => ({
  CodeFileTree: ({
    files,
    editablePaths,
  }: {
    files: { path: string }[]
    editablePaths: string[]
  }) => (
    <ul aria-label='Arquivos do projeto'>
      {files.map((file) => (
        <li key={file.path}>
          {file.path}
          {editablePaths.includes(file.path) ? ' editável' : ' somente leitura'}
        </li>
      ))}
    </ul>
  ),
}))

const useQuestionMock = vi.mocked(useHtmlCssJsQuestion)
const QUESTION: HtmlQuestion = {
  key: 'web-1',
  kind: 'html_css_js',
  prompt: 'Crie uma página de apresentação acessível.',
  initialFiles: [
    { path: 'index.html', content: '<main></main>', editable: true },
    { path: 'vite.config.js', content: 'export default {}', editable: false },
  ],
  entrypoint: 'index.html',
  editablePaths: ['index.html'],
  fixedDependencies: [{ name: 'vite', version: '7.0.0' }],
  permittedCommands: [{ id: 'dev', executable: 'npm', arguments: ['run', 'dev'] }],
  criteria: [
    { key: 'semantic', name: 'HTML semântico', weightPercentage: 65 },
    { key: 'responsive', name: 'Layout responsivo', weightPercentage: 35 },
  ],
}

type Controller = ReturnType<typeof useHtmlCssJsQuestion>
function createController(overrides: Partial<Controller> = {}): Controller {
  return {
    displayFiles: [
      { path: 'index.html', content: '<main>rascunho</main>' },
      { path: 'vite.config.js', content: 'export default {}' },
    ],
    editablePaths: ['index.html'],
    selectedPath: 'index.html',
    practiceStatus: 'ready',
    previewUrl: 'https://preview-123.webcontainer-api.io/',
    terminalText: 'VITE pronto',
    practiceTab: 'preview',
    isSaving: false,
    hasSaveError: false,
    hasFileError: false,
    hasAssessError: false,
    isAssessing: false,
    isFrozen: false,
    isDraftInvalidated: false,
    draftLoaded: true,
    generation: 2,
    handleAssess: vi.fn(async () => undefined),
    handleFileChange: vi.fn(),
    handleSelectFile: vi.fn(),
    handleSelectPracticeTab: vi.fn(),
    ...overrides,
  }
}

function createProps(
  overrides: Partial<HtmlCssJsQuestionProps> = {},
): HtmlCssJsQuestionProps {
  return {
    question: QUESTION,
    accountId: 'account-1',
    goalId: 'goal-1',
    skillId: 'skill-1',
    competencyId: 'competency-1',
    activityId: 'activity-1',
    activityRevision: 'revision-1',
    activeQuestionKeys: ['web-1'],
    isOnlineAuthority: true,
    questionNumber: 2,
    totalQuestions: 3,
    draftStore: {
      read: vi.fn(async () => null),
      write: vi.fn(async () => 1),
      tombstone: vi.fn(async () => 1),
      clearTombstone: vi.fn(async () => 2),
      tombstoneActivity: vi.fn(async () => undefined),
      tombstoneStaleActivity: vi.fn(async () => undefined),
      subscribe: vi.fn(() => () => undefined),
    },
    onAssess: vi.fn(),
    ...overrides,
  }
}

describe('HtmlCssJsQuestion', () => {
  beforeEach(() => {
    useQuestionMock.mockReset()
    useQuestionMock.mockReturnValue(createController())
  })
  afterEach(cleanup)

  it('shows the current rubric and only the isolated preview and terminal tabs', () => {
    render(<HtmlCssJsQuestion {...createProps()} />)
    expect(screen.getByText('HTML semântico')).toBeVisible()
    expect(screen.getByText('Peso 65%')).toBeVisible()
    expect(screen.getByText('index.html editável')).toBeVisible()
    expect(screen.getByText('vite.config.js somente leitura')).toBeVisible()
    expect(
      screen.queryByRole('button', { name: /novo arquivo|executar|http/i }),
    ).not.toBeInTheDocument()
    const preview = screen.getByTitle('Prévia isolada da página')
    const url = new URL(preview.getAttribute('src') ?? '')
    expect(preview).toHaveAttribute('sandbox', 'allow-scripts')
    expect(preview).toHaveAttribute('referrerpolicy', 'no-referrer')
    expect(url.protocol).toBe('https:')
    expect(url.origin).not.toBe(window.location.origin)
  })

  it('routes file editing and rubric assessment through the owning hook', () => {
    const controller = createController()
    useQuestionMock.mockReturnValue(controller)
    render(<HtmlCssJsQuestion {...createProps()} />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Editor de arquivo' }), {
      target: { value: '<main>editado</main>' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Avaliar questão' }))
    expect(controller.handleFileChange).toHaveBeenCalledWith(
      'index.html',
      '<main>editado</main>',
    )
    expect(controller.handleAssess).toHaveBeenCalledOnce()
    expect(screen.queryByRole('button', { name: 'Executar' })).not.toBeInTheDocument()
  })

  it('supports keyboard navigation between the preview and terminal tabs', async () => {
    const user = userEvent.setup()
    const controller = createController()
    useQuestionMock.mockReturnValue(controller)
    render(<HtmlCssJsQuestion {...createProps()} />)

    await user.tab()
    await user.tab()
    await user.tab()
    await user.tab()
    expect(screen.getByRole('tab', { name: 'Terminal' })).toHaveFocus()
    await user.keyboard('{Enter}')

    expect(controller.handleSelectPracticeTab).toHaveBeenCalledWith('terminal')
  })

  it('keeps editing available when practice or local storage is unavailable', () => {
    useQuestionMock.mockReturnValue(
      createController({
        practiceStatus: 'unavailable',
        previewUrl: null,
        hasSaveError: true,
        hasAssessError: true,
      }),
    )
    render(<HtmlCssJsQuestion {...createProps()} />)
    expect(screen.getByText(/não foi possível salvar o rascunho/i)).toBeVisible()
    expect(screen.getByText(/Prática indisponível/i)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
    expect(
      screen.getByRole('textbox', { name: 'Editor de arquivo' }),
    ).not.toHaveAttribute('readonly')
  })

  it('shows practice output in the Terminal and preserves the assessed editor as read-only', () => {
    useQuestionMock.mockReturnValue(
      createController({
        practiceTab: 'terminal',
        isFrozen: true,
        terminalText: 'Servidor iniciado pela questão.',
      }),
    )
    render(<HtmlCssJsQuestion {...createProps({ disabled: true })} />)
    expect(
      screen.getByRole('log', { name: 'Saída do Terminal de prática' }),
    ).toHaveTextContent('Servidor iniciado pela questão.')
    expect(screen.getByRole('textbox', { name: 'Editor de arquivo' })).toHaveAttribute(
      'readonly',
    )
    expect(screen.getByText(/não influenciam sua nota/i)).toBeVisible()
  })
})
