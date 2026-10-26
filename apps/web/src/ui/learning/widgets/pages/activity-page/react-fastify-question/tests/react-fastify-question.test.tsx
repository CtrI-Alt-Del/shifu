import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CodeEditorProps } from '@/ui/learning/widgets/components/code-editor'
import { createReactDraftStoreMock } from '../../tests/react-draft-store-mock'
import { ReactFastifyQuestion } from '..'
import {
  useReactFastifyQuestion,
  type ReactFastifyQuestionProps,
} from '../use-react-fastify-question'
vi.mock('../use-react-fastify-question', () => ({ useReactFastifyQuestion: vi.fn() }))
vi.mock('@/ui/learning/widgets/components/code-editor', () => ({
  CodeEditor: ({ readOnly, files }: CodeEditorProps) => (
    <textarea
      aria-label='Código integrado'
      readOnly={readOnly}
      defaultValue={files[0]?.content}
    />
  ),
}))
const useReactFastifyQuestionMock = vi.mocked(useReactFastifyQuestion)
const QUESTION: ReactFastifyQuestionProps['question'] = {
  key: 'integrated',
  kind: 'react_fastify',
  prompt: 'Conecte a lista à API',
  initialFiles: [
    { path: 'src/App.tsx', content: 'frontend', editable: true },
    { path: 'server.js', content: 'api', editable: true },
  ],
  editablePaths: ['src/App.tsx', 'server.js'],
  frontendEntrypoint: 'src/App.tsx',
  apiEntrypoint: 'server.js',
  frontendCommandId: 'web',
  apiCommandId: 'api',
  fixedDependencies: [],
  permittedCommands: [],
  httpExamples: [],
  additionalFilePolicy: {
    allowedDirectories: ['src'],
    allowedExtensions: ['.tsx'],
    maxFiles: 2,
  },
  criteria: [
    { key: 'integration', name: 'Integração com a API', weightPercentage: 65 },
    { key: 'ui', name: 'Interface', weightPercentage: 35 },
  ],
}
function props(): ReactFastifyQuestionProps {
  return {
    question: QUESTION,
    draftStore: createReactDraftStoreMock(),
    accountId: 'a',
    activityId: 'activity',
    activityRevision: 'revision',
    activeQuestionKeys: ['integrated'],
    isOnlineAuthority: true,
    questionNumber: 2,
    totalQuestions: 3,
    onAssess: vi.fn(),
  }
}
function controller(): ReturnType<typeof useReactFastifyQuestion> {
  return {
    files: QUESTION.initialFiles.map(({ path, content }) => ({ path, content })),
    displayFiles: QUESTION.initialFiles.map(({ path, content }) => ({ path, content })),
    selectedPath: 'src/App.tsx',
    editablePaths: ['src/App.tsx', 'server.js'],
    editorEditablePaths: ['src/App.tsx', 'server.js'],
    additionalFilesCount: 0,
    draftLoaded: true,
    draftGeneration: 1,
    isSaving: false,
    hasSaveError: false,
    isAssessing: false,
    hasAssessError: false,
    frontendStatus: 'ready',
    apiStatus: 'ready',
    previewUrl: 'https://preview.webcontainer.io',
    terminalText: 'API pronta',
    newFilePath: '',
    hasFileError: false,
    isDraftInvalidated: false,
    isActivityLocked: false,
    totalSourceBytes: 70,
    isFrozen: false,
    handleRequest: vi.fn(async () => ({
      status: 200,
      body: '[]',
      headers: [],
      truncated: false,
    })),
    handleRunCommand: vi.fn(async () => undefined),
    handleAddFile: vi.fn(),
    handleAssess: vi.fn(async () => undefined),
    handleFileChange: vi.fn(),
    handleSelectFile: vi.fn(),
    handleNewFilePathChange: vi.fn(),
  }
}
describe('ReactFastifyQuestion', () => {
  beforeEach(() => useReactFastifyQuestionMock.mockReturnValue(controller()))
  afterEach(cleanup)
  it('renders curricular weights, separate process status and an isolated preview', () => {
    render(<ReactFastifyQuestion {...props()} />)
    expect(screen.getByText('Integração com a API')).toBeVisible()
    expect(screen.getByText('Peso 65%')).toBeVisible()
    expect(screen.getByText(/Frontend: Pronto · API: Pronto/)).toBeVisible()
    expect(screen.getByTitle('Prévia isolada React + Fastify')).toHaveAttribute(
      'sandbox',
      'allow-scripts allow-same-origin',
    )
    const preview = screen.getByTitle('Prévia isolada React + Fastify')
    expect(preview).toHaveAttribute('referrerpolicy', 'no-referrer')
    expect(preview).not.toHaveAttribute('allow')
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
    expect(screen.queryByRole('button', { name: 'Executar' })).not.toBeInTheDocument()
  })
  it('exposes one explorer file-plus action and delegates creation and assessment', () => {
    const state = controller()
    useReactFastifyQuestionMock.mockReturnValue(state)
    render(<ReactFastifyQuestion {...props()} />)
    fireEvent.mouseDown(screen.getByRole('tab', { name: 'Arquivos' }), {
      button: 0,
      ctrlKey: false,
    })
    fireEvent.click(screen.getByRole('tab', { name: 'Arquivos' }))
    expect(screen.getAllByRole('button', { name: 'Novo arquivo' })).toHaveLength(1)
    fireEvent.change(screen.getByRole('textbox', { name: 'Caminho do novo arquivo' }), {
      target: { value: 'src/Novo.tsx' },
    })
    expect(state.handleNewFilePathChange).toHaveBeenCalledWith('src/Novo.tsx')
    fireEvent.click(screen.getByRole('button', { name: 'Novo arquivo' }))
    expect(state.handleAddFile).toHaveBeenCalledOnce()
    fireEvent.click(screen.getByRole('button', { name: 'Avaliar questão' }))
    expect(state.handleAssess).toHaveBeenCalledOnce()
  })
  it.each([
    { draftLoaded: false },
    { isSaving: true },
    { hasSaveError: true },
    { hasFileError: true },
    { hasAssessError: true },
    { isDraftInvalidated: true },
  ])('announces draft and recovery state %j', (overrides) => {
    useReactFastifyQuestionMock.mockReturnValue({ ...controller(), ...overrides })
    render(<ReactFastifyQuestion {...props()} />)
    if (overrides.draftLoaded === false)
      expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeDisabled()
    if (overrides.hasSaveError)
      expect(screen.getByText(/Há risco de perda/)).toBeVisible()
    if (overrides.hasFileError || overrides.hasAssessError)
      expect(screen.getByRole('alert')).toBeVisible()
    if (overrides.isDraftInvalidated)
      expect(screen.getByRole('textbox', { name: 'Código integrado' })).toHaveAttribute(
        'readonly',
      )
    if (overrides.isSaving)
      expect(screen.getByText(/Salvando neste navegador/)).toBeVisible()
  })
  it('keeps editing and assessment available when practice is unavailable', () => {
    useReactFastifyQuestionMock.mockReturnValue({
      ...controller(),
      frontendStatus: 'unavailable',
      apiStatus: 'unavailable',
      previewUrl: null,
    })
    render(<ReactFastifyQuestion {...props()} />)
    expect(screen.getByText(/Você pode continuar editando/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeEnabled()
    expect(screen.getByRole('textbox', { name: 'Código integrado' })).not.toHaveAttribute(
      'readonly',
    )
  })
  it('freezes editor and disables assessment while showing the evaluated response', () => {
    useReactFastifyQuestionMock.mockReturnValue({ ...controller(), isFrozen: true })
    render(<ReactFastifyQuestion {...props()} readOnly />)
    expect(screen.getByRole('textbox', { name: 'Código integrado' })).toHaveAttribute(
      'readonly',
    )
    expect(screen.getByRole('button', { name: 'Avaliar questão' })).toBeDisabled()
  })
})
