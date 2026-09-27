import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useCodeEditor } from '../use-code-editor'

const FILES = [
  { path: 'main.js', content: 'one' },
  { path: 'helper.js', content: 'two' },
]

describe('useCodeEditor', () => {
  it('uses the selected file and only changes editable source', () => {
    const onFileChange = vi.fn()
    const editableFile = renderHook(() =>
      useCodeEditor({ files: FILES, editablePaths: ['main.js'], onFileChange }),
    )
    expect(editableFile.result.current.selectedPath).toBe('main.js')
    act(() => editableFile.result.current.handleChange('updated'))
    expect(onFileChange).toHaveBeenCalledWith('main.js', 'updated')
    const readOnlyFile = renderHook(() =>
      useCodeEditor({
        files: FILES,
        editablePaths: ['main.js'],
        selectedPath: 'helper.js',
        onFileChange,
      }),
    )
    expect(readOnlyFile.result.current.selectedPath).toBe('helper.js')
    expect(readOnlyFile.result.current.isReadOnly).toBe(true)
    act(() => readOnlyFile.result.current.handleChange('blocked'))
    expect(onFileChange).toHaveBeenCalledTimes(1)
  })

  it('treats all files as read only when frozen', () => {
    const { result } = renderHook(() =>
      useCodeEditor({ files: FILES, editablePaths: ['main.js'], readOnly: true }),
    )
    expect(result.current.isReadOnly).toBe(true)
  })

  it('uses the file selected in the question sidebar', () => {
    const { result } = renderHook(() =>
      useCodeEditor({
        files: FILES,
        editablePaths: ['main.js'],
        selectedPath: 'helper.js',
      }),
    )
    expect(result.current.selectedFile?.content).toBe('two')
    expect(result.current.isReadOnly).toBe(true)
  })
})
