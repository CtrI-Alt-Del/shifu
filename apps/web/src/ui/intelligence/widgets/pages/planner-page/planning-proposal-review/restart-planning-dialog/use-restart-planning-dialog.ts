import { useEffect, useRef, useState, type FormEvent } from 'react'

import { PLANNING_INTENT_MAX_LENGTH } from '@/core/intelligence/planning-session'

export type RestartPlanningDialogProps = {
  isOpen: boolean
  initialIntent: string
  isSubmitting: boolean
  errorMessage: string | null
  restoreFocusRef: React.RefObject<HTMLButtonElement | null>
  onClose: () => void
  onSubmit: (initialIntent: string) => void
}

const EMPTY_INTENT_MESSAGE = 'Descreva o que você quer aprender antes de continuar.'
const LONG_INTENT_MESSAGE = `Resuma sua intenção em até ${PLANNING_INTENT_MAX_LENGTH} caracteres.`

export function useRestartPlanningDialog({
  isOpen,
  initialIntent,
  isSubmitting,
  onSubmit,
}: RestartPlanningDialogProps) {
  const [intent, setIntent] = useState(initialIntent)
  const [validationMessage, setValidationMessage] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    // Every opening starts from the active intention of the planning.
    if (isOpen) {
      setIntent(initialIntent)
      setValidationMessage(null)
    }
  }, [initialIntent, isOpen])

  function handleIntentChange(value: string) {
    setIntent(value)
    if (validationMessage) setValidationMessage(null)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedIntent = intent.trim()
    if (!trimmedIntent) {
      setValidationMessage(EMPTY_INTENT_MESSAGE)
      textareaRef.current?.focus()
      return
    }
    if (trimmedIntent.length > PLANNING_INTENT_MAX_LENGTH) {
      setValidationMessage(LONG_INTENT_MESSAGE)
      textareaRef.current?.focus()
      return
    }
    if (isSubmitting) return
    onSubmit(trimmedIntent)
  }

  function handleOpenAutoFocus(event: Event) {
    event.preventDefault()
    textareaRef.current?.focus()
  }

  return {
    intent,
    validationMessage,
    textareaRef,
    handleIntentChange,
    handleSubmit,
    handleOpenAutoFocus,
  }
}
