import Editor from '@monaco-editor/react'
import type { ComponentProps } from 'react'
import { type CodeEditorProps, useCodeEditor } from './use-code-editor'

export type { CodeEditorProps, EditorFile } from './use-code-editor'

const CODE_EDITOR_THEME = 'shifu-code-dark'

const defineCodeEditorTheme: NonNullable<ComponentProps<typeof Editor>['beforeMount']> = (
  monaco,
) => {
  monaco.editor.defineTheme(CODE_EDITOR_THEME, {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'keyword', foreground: 'FF6EB4' },
      { token: 'keyword.control', foreground: 'FF6EB4' },
      { token: 'identifier', foreground: 'B5B0FF' },
      { token: 'variable', foreground: 'B5B0FF' },
      { token: 'parameter', foreground: 'B5B0FF' },
      { token: 'type.identifier', foreground: '91D7E3' },
      { token: 'function', foreground: 'B5B0FF' },
      { token: 'method', foreground: 'B5B0FF' },
      { token: 'property', foreground: '91D7E3' },
      { token: 'string', foreground: 'A6E3A1' },
      { token: 'string.escape', foreground: 'FFD580' },
      { token: 'number', foreground: 'F9B387' },
      { token: 'number.float', foreground: 'F9B387' },
      { token: 'operator', foreground: 'FF8AC7' },
      { token: 'comment', foreground: '7E9B84', fontStyle: 'italic' },
      { token: 'regexp', foreground: 'F38BA8' },
    ],
    colors: {
      'editor.background': '#1B1B1B',
      'editor.foreground': '#E4E4E7',
      'editorGutter.background': '#1B1B1B',
      'editorLineNumber.foreground': '#74747C',
      'editorLineNumber.activeForeground': '#D8D8DF',
      'editorCursor.foreground': '#F4D35E',
      'editor.selectionBackground': '#53476B80',
      'editor.inactiveSelectionBackground': '#45404F80',
      'editor.lineHighlightBackground': '#FFFFFF08',
    },
  })
  monaco.editor.setTheme(CODE_EDITOR_THEME)
}

function languageForFile(path: string) {
  const extension = path.split('.').at(-1)?.toLowerCase()
  if (extension === 'js') return 'javascript'
  if (extension === 'json') return 'json'
  return 'plaintext'
}

export const CodeEditor = (props: CodeEditorProps) => {
  const { isReadOnly, selectedFile, selectedPath, handleChange } = useCodeEditor(props)
  return (
    <section
      aria-label='Editor de código'
      className='flex min-h-[28rem] min-w-0 flex-col bg-card lg:h-full lg:min-h-0'
    >
      <div className='flex min-h-12 items-center gap-2 border-b border-border px-3 lg:h-10 lg:min-h-10'>
        {selectedPath ? (
          <>
            <span
              aria-hidden='true'
              className='size-1.5 shrink-0 rounded-full bg-amber-400'
            />
            <span className='min-w-0 truncate font-mono text-xs text-muted-foreground'>
              {selectedPath}
            </span>
          </>
        ) : (
          <span className='min-w-0 truncate font-mono text-xs text-muted-foreground'>
            Nenhum arquivo
          </span>
        )}
        {isReadOnly ? (
          <span className='ml-auto text-xs text-muted-foreground'>Somente leitura</span>
        ) : null}
      </div>
      <fieldset
        className='min-h-[25rem] min-w-0 flex-1 overflow-hidden lg:min-h-0'
        aria-label={selectedFile ? `Código: ${selectedFile.path}` : 'Código'}
      >
        {selectedFile ? (
          <Editor
            height='100%'
            path={selectedFile.path}
            language={languageForFile(selectedFile.path)}
            theme={CODE_EDITOR_THEME}
            beforeMount={defineCodeEditorTheme}
            value={selectedFile.content}
            onChange={handleChange}
            options={{
              readOnly: isReadOnly,
              minimap: { enabled: false },
              automaticLayout: true,
              wordWrap: 'on',
              scrollBeyondLastLine: false,
              bracketPairColorization: { enabled: true },
              guides: { bracketPairs: true },
              ariaLabel: `Código: ${selectedFile.path}`,
            }}
          />
        ) : (
          <p className='p-4 text-sm'>Nenhum arquivo disponível.</p>
        )}
      </fieldset>
    </section>
  )
}
