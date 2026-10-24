import { type FormEvent, useCallback, useState } from 'react'

export const MEMORY_CONTENT_MAX_LENGTH = 280

export type UseMemoryEditFormInput = {
  initialContent: string
  onSave: (content: string) => void
  onCancel: () => void
}

export function useMemoryEditForm({
  initialContent,
  onSave,
  onCancel,
}: UseMemoryEditFormInput) {
  const [content, setContent] = useState(initialContent)
  const [hasAttemptedSave, setHasAttemptedSave] = useState(false)
  const trimmedContent = content.trim()
  const characterCount = [...trimmedContent].length
  const validationError =
    characterCount === 0
      ? 'Escreva o conteúdo da memória.'
      : characterCount > MEMORY_CONTENT_MAX_LENGTH
        ? `Use no máximo ${MEMORY_CONTENT_MAX_LENGTH} caracteres.`
        : null
  const visibleError =
    hasAttemptedSave || characterCount > MEMORY_CONTENT_MAX_LENGTH
      ? validationError
      : null

  // A stable callback ref moves focus into the field once, when the form opens.
  const handleTextareaRef = useCallback(function handleTextareaRef(
    element: HTMLTextAreaElement | null,
  ) {
    element?.focus()
  }, [])

  function handleContentChange(value: string) {
    setContent(value)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setHasAttemptedSave(true)
    if (validationError) return
    onSave(trimmedContent)
  }

  function handleCancel() {
    onCancel()
  }

  return {
    content,
    characterCount,
    visibleError,
    handleTextareaRef,
    handleContentChange,
    handleSubmit,
    handleCancel,
  }
}
