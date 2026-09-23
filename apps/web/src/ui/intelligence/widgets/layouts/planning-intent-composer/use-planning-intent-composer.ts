import { useRef, useState, type FormEvent } from 'react'

import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { useStartPlanningAction } from '@/ui/intelligence/hooks/use-start-planning-action'

const EMPTY_INTENT_VALIDATION_MESSAGE =
  'Descreva o que você quer aprender antes de continuar.'
const START_PLANNING_ERROR_MESSAGE =
  'Não foi possível iniciar o planejamento agora. Tente novamente.'

export function usePlanningIntentComposer() {
  const { navigateToPlanner } = useNavigation()
  const { error: startPlanningError, isPending, startPlanning } = useStartPlanningAction()
  const [intent, setIntent] = useState('')
  const [validationMessage, setValidationMessage] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleIntentChange(value: string) {
    setIntent(value)
    if (validationMessage) setValidationMessage(null)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedIntent = intent.trim()

    if (!trimmedIntent) {
      setValidationMessage(EMPTY_INTENT_VALIDATION_MESSAGE)
      textareaRef.current?.focus()
      return
    }

    startPlanning(trimmedIntent, {
      onSuccess: (session) => {
        navigateToPlanner(session.id)
      },
    })
  }

  return {
    intent,
    isPending,
    startPlanningErrorMessage: startPlanningError ? START_PLANNING_ERROR_MESSAGE : null,
    textareaRef,
    validationMessage,
    handleIntentChange,
    handleSubmit,
  }
}
