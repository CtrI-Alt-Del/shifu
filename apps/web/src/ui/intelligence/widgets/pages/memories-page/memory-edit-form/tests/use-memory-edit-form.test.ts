import { act, cleanup, renderHook } from '@testing-library/react'
import type { FormEvent } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { MEMORY_CONTENT_MAX_LENGTH, useMemoryEditForm } from '../use-memory-edit-form'

const onSaveMock = vi.fn()
const onCancelMock = vi.fn()
const preventDefaultMock = vi.fn()

function submitEvent() {
  return { preventDefault: preventDefaultMock } as unknown as FormEvent<HTMLFormElement>
}

function renderForm(initialContent = 'Prefiro exemplos curtos.') {
  return renderHook(() =>
    useMemoryEditForm({ initialContent, onSave: onSaveMock, onCancel: onCancelMock }),
  )
}

describe('useMemoryEditForm', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(cleanup)

  it('starts with the current content and its character count', () => {
    const { result } = renderForm()

    expect(result.current.content).toBe('Prefiro exemplos curtos.')
    expect(result.current.characterCount).toBe(24)
    expect(result.current.visibleError).toBeNull()
  })

  it('saves the trimmed content', () => {
    const { result } = renderForm()

    act(() => result.current.handleContentChange('  Prefiro Python.  '))
    act(() => result.current.handleSubmit(submitEvent()))

    expect(preventDefaultMock).toHaveBeenCalled()
    expect(onSaveMock).toHaveBeenCalledWith('Prefiro Python.')
  })

  it('blocks an empty save and reveals the validation error only after a submit', () => {
    const { result } = renderForm()

    act(() => result.current.handleContentChange('   '))
    expect(result.current.visibleError).toBeNull()
    act(() => result.current.handleSubmit(submitEvent()))

    expect(onSaveMock).not.toHaveBeenCalled()
    expect(result.current.visibleError).toBe('Escreva o conteúdo da memória.')
  })

  it('counts code points and rejects more than the maximum immediately', () => {
    const { result } = renderForm()

    act(() => result.current.handleContentChange('😀'.repeat(MEMORY_CONTENT_MAX_LENGTH)))
    expect(result.current.characterCount).toBe(MEMORY_CONTENT_MAX_LENGTH)
    expect(result.current.visibleError).toBeNull()

    act(() =>
      result.current.handleContentChange('😀'.repeat(MEMORY_CONTENT_MAX_LENGTH + 1)),
    )
    expect(result.current.visibleError).toBe('Use no máximo 280 caracteres.')
    act(() => result.current.handleSubmit(submitEvent()))

    expect(onSaveMock).not.toHaveBeenCalled()
  })

  it('accepts content at the exact maximum', () => {
    const { result } = renderForm()
    const content = 'a'.repeat(MEMORY_CONTENT_MAX_LENGTH)

    act(() => result.current.handleContentChange(content))
    act(() => result.current.handleSubmit(submitEvent()))

    expect(onSaveMock).toHaveBeenCalledWith(content)
  })

  it('focuses the content field when it is attached and ignores detaching', () => {
    const { result } = renderForm()
    const textarea = document.createElement('textarea')
    document.body.append(textarea)

    act(() => result.current.handleTextareaRef(null))
    expect(textarea).not.toHaveFocus()
    act(() => result.current.handleTextareaRef(textarea))

    expect(textarea).toHaveFocus()
    textarea.remove()
  })

  it('delegates cancellation', () => {
    const { result } = renderForm()

    act(() => result.current.handleCancel())

    expect(onCancelMock).toHaveBeenCalledOnce()
  })
})
