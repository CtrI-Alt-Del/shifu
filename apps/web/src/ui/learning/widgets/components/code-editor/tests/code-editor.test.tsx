import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CodeEditor } from '..'
import { useCodeEditor } from '../use-code-editor'

vi.mock('../use-code-editor', () => ({ useCodeEditor: vi.fn() }))
vi.mock('@monaco-editor/react', () => ({
  default: ({
    value,
    language,
    theme,
  }: {
    value: string
    language: string
    theme: string
  }) => (
    <textarea
      aria-label='Código simulado'
      data-language={language}
      data-theme={theme}
      value={value}
      readOnly
    />
  ),
}))
const useCodeEditorMock = vi.mocked(useCodeEditor)

describe('CodeEditor', () => {
  afterEach(cleanup)
  beforeEach(() =>
    useCodeEditorMock.mockReturnValue({
      isReadOnly: false,
      selectedFile: { path: 'main.js', content: 'console.log(1)' },
      selectedPath: 'main.js',
      handleChange: vi.fn(),
    }),
  )

  it('renders the selected file path and editor without a duplicate file tree', () => {
    const onFileChange = vi.fn()
    render(
      <CodeEditor
        files={[{ path: 'main.js', content: 'console.log(1)' }]}
        editablePaths={['main.js']}
        onFileChange={onFileChange}
      />,
    )
    expect(screen.getByRole('group', { name: 'Código: main.js' })).toBeVisible()
    expect(screen.getByText('main.js')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Arquivos' })).not.toBeInTheDocument()
    expect(
      screen.queryByRole('tree', { name: 'Arquivos do projeto' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Código simulado' })).toHaveAttribute(
      'data-language',
      'javascript',
    )
    expect(screen.getByRole('textbox', { name: 'Código simulado' })).toHaveAttribute(
      'data-theme',
      'shifu-code-dark',
    )
  })

  it('uses plain text highlighting for files without a supported language', () => {
    useCodeEditorMock.mockReturnValue({
      isReadOnly: false,
      selectedFile: { path: 'README.md', content: 'Instructions' },
      selectedPath: 'README.md',
      handleChange: vi.fn(),
    })
    render(<CodeEditor files={[{ path: 'README.md', content: 'Instructions' }]} />)
    expect(screen.getByRole('textbox', { name: 'Código simulado' })).toHaveAttribute(
      'data-language',
      'plaintext',
    )
  })

  it('labels frozen source as read only', () => {
    useCodeEditorMock.mockReturnValue({
      isReadOnly: true,
      selectedFile: { path: 'main.js', content: 'sent' },
      selectedPath: 'main.js',
      handleChange: vi.fn(),
    })
    render(<CodeEditor files={[{ path: 'main.js', content: 'sent' }]} readOnly />)
    expect(screen.getByText('Somente leitura')).toBeVisible()
  })
})
