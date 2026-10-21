import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactQuestion as ReactQuestionModel } from '@/core/learning/choice-activity'
import type { CodeEditorProps } from '@/ui/learning/widgets/components/code-editor'
import { ReactQuestion } from '..'
import { type ReactQuestionProps, useReactQuestion } from '../use-react-question'

vi.mock('../use-react-question', () => ({ useReactQuestion: vi.fn() }))
vi.mock('@/ui/learning/widgets/components/code-editor', () => ({
  CodeEditor: ({ files, selectedPath, readOnly, onFileChange }: CodeEditorProps) => {
    const file = files.find(({ path }) => path === selectedPath) ?? files[0]
    return (
      <textarea
        aria-label='Código do arquivo'
        value={file?.content ?? ''}
        readOnly={readOnly}
        onChange={(event) => file && onFileChange?.(file.path, event.target.value)}
      />
    )
  },
}))
const useReactQuestionMock = vi.mocked(useReactQuestion)
const QUESTION: ReactQuestionModel = {
  key: 'react-1',
  kind: 'react',
  prompt: 'Monte uma tela de boas-vindas.',
  initialFiles: [
    { path: 'src/App.tsx', content: 'export default function App() {}', editable: true },
  ],
  entrypoint: 'src/main.tsx',
  editablePaths: ['src/App.tsx'],
  fixedDependencies: [{ name: 'react', version: '19.0.0' }],
  permittedCommands: [],
  additionalFilePolicy: {
    allowedDirectories: ['src'],
    allowedExtensions: ['.tsx'],
    maxFiles: 2,
  },
  criteria: [{ key: 'complete', name: 'Completude', weightPercentage: 100 }],
}
type Controller = ReturnType<typeof useReactQuestion>
function createController(overrides: Partial<Controller> = {}): Controller {
  return {
    files: [{ path: 'src/App.tsx', content: 'edited' }],
    displayFiles: [{ path: 'src/App.tsx', content: 'edited' }],
    selectedPath: 'src/App.tsx',
    editablePaths: ['src/App.tsx'],
    editorEditablePaths: ['src/App.tsx'],
    additionalFilesCount: 0,
    draftLoaded: true,
    draftGeneration: 1,
    isSaving: false,
    hasSaveError: false,
    isAssessing: false,
    hasAssessError: false,
    status: 'ready',
    previewUrl: 'https://preview-abc.local-corp.webcontainer-api.io/',
    terminalText: 'Prática pronta',
    newFilePath: '',
    hasFileError: false,
    isDraftInvalidated: false,
    isActivityLocked: false,
    totalSourceBytes: 32,
    isFrozen: false,
    handleAddFile: vi.fn(),
    handleAssess: vi.fn(async () => undefined),
    handleFileChange: vi.fn(),
    handleSelectFile: vi.fn(),
    handleNewFilePathChange: vi.fn(),
    ...overrides,
  }
}
function createProps(overrides: Partial<ReactQuestionProps> = {}): ReactQuestionProps {
  return {
    question: QUESTION,
    draftStore: {
      read: vi.fn(async () => null),
      write: vi.fn(async () => 1),
      tombstone: vi.fn(async () => 1),
      clearTombstone: vi.fn(async () => 2),
      tombstoneActivity: vi.fn(async () => undefined),
      tombstoneStaleActivity: vi.fn(async () => undefined),
      subscribe: vi.fn(() => () => undefined),
    },
    accountId: 'account-1',
    goalId: 'goal-1',
    skillId: 'skill-1',
    competencyId: 'competency-1',
    activityId: 'activity-1',
    activityRevision: 'revision-1',
    activeQuestionKeys: ['react-1'],
    isOnlineAuthority: true,
    questionNumber: 1,
    totalQuestions: 1,
    onAssess: vi.fn(),
    ...overrides,
  }
}
describe('ReactQuestion', () => {
  beforeEach(() => {
    useReactQuestionMock.mockReset()
    useReactQuestionMock.mockReturnValue(createController())
  })
  afterEach(cleanup)
  it('shows the curricular policy and isolates the preview in a distinct HTTPS origin', () => {
    render(<ReactQuestion {...createProps()} />)
    expect(screen.getByText('Completude')).toBeVisible()
    expect(screen.getByText(/Pastas: src · extensões: .tsx · 0\/2/)).toBeVisible()
    const preview = screen.getByTitle('Prévia isolada da aplicação React')
    const url = new URL(preview.getAttribute('src') ?? '')
    expect(preview).toHaveAttribute('sandbox', 'allow-scripts')
    expect(url.protocol).toBe('https:')
    expect(url.hostname).toMatch(/\.webcontainer-api\.io$/)
    expect(url.origin).not.toBe(window.location.origin)
    expect(screen.getByRole('log')).toHaveTextContent('Prática pronta')
  })
  it('delegates editing, file creation and assessment through the widget controls', () => {
    const controller = createController()
    useReactQuestionMock.mockReturnValue(controller)
    render(<ReactQuestion {...createProps()} />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Código do arquivo' }), {
      target: { value: 'new source' },
    })
    fireEvent.change(screen.getByRole('textbox', { name: 'Caminho do novo arquivo' }), {
      target: { value: 'src/Badge.tsx' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Criar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Avaliar questão' }))
    expect(controller.handleFileChange).toHaveBeenCalledWith('src/App.tsx', 'new source')
    expect(controller.handleNewFilePathChange).toHaveBeenCalledWith('src/Badge.tsx')
    expect(controller.handleAddFile).toHaveBeenCalledOnce()
    expect(controller.handleAssess).toHaveBeenCalledOnce()
    expect(screen.getByRole('textbox', { name: 'Código do arquivo' })).toHaveValue(
      'edited',
    )
  })
  it('shows authority validation and disables assessment until restoration completes', () => {
    useReactQuestionMock.mockReturnValue(
      createController({ draftLoaded: false, status: 'booting', previewUrl: null }),
    )
    render(<ReactQuestion {...createProps()} />)
    expect(screen.getByText('Validando a Atividade…')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: 'Código do arquivo' })).toHaveAttribute(
      'readonly',
    )
    expect(screen.getByText('Iniciando a prévia…')).toBeVisible()
  })
  it('preserves editing and assessment when the runtime is unavailable', () => {
    useReactQuestionMock.mockReturnValue(
      createController({
        status: 'unavailable',
        previewUrl: null,
        hasSaveError: true,
        hasAssessError: true,
        hasFileError: true,
      }),
    )
    render(<ReactQuestion {...createProps()} />)
    expect(screen.getByText(/Não foi possível salvar localmente/)).toBeVisible()
    expect(screen.getByText(/A prévia não está disponível/)).toBeVisible()
    expect(
      screen.getByText('Não foi possível avaliar a questão. Tente novamente.'),
    ).toBeVisible()
    expect(screen.getByText(/Arquivo fora da política permitida/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
    expect(
      screen.getByRole('textbox', { name: 'Código do arquivo' }),
    ).not.toHaveAttribute('readonly')
  })
  it('freezes preliminary files and disables controls while assessment is pending', () => {
    useReactQuestionMock.mockReturnValue(
      createController({ isFrozen: true, isAssessing: true }),
    )
    render(<ReactQuestion {...createProps()} />)
    expect(screen.getByRole('button', { name: 'Avaliando…' })).toBeDisabled()
    expect(
      screen.queryByRole('textbox', { name: 'Caminho do novo arquivo' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Código do arquivo' })).toHaveAttribute(
      'readonly',
    )
    expect(screen.getByRole('textbox', { name: 'Código do arquivo' })).toHaveValue(
      'edited',
    )
  })
  it('blocks invalidated drafts and explains diagnostic draft exclusion', () => {
    useReactQuestionMock.mockReturnValue(createController({ isDraftInvalidated: true }))
    const { rerender } = render(<ReactQuestion {...createProps()} />)
    expect(screen.getByText(/Rascunho invalidado/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeDisabled()
    rerender(<ReactQuestion {...createProps({ isDiagnostic: true })} />)
    expect(screen.getByText('Diagnóstico não salva rascunhos.')).toBeVisible()
  })
})
