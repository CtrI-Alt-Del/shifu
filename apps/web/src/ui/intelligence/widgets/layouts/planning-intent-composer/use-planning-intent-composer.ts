import { useRef, useState, type FormEvent } from 'react'

import { useNavigation } from '@/ui/shared/hooks/use-navigation'
import { useAiQuotaBlock } from '@/ui/intelligence/hooks/use-ai-quota-block'
import { isPlanningQuotaExhaustedError } from '@/ui/intelligence/hooks/planning-request-error'
import { useStartPlanningAction } from '@/ui/intelligence/hooks/use-start-planning-action'
import { registerPlanningEntry } from '@/ui/intelligence/planning-entry'

const EMPTY_INTENT_VALIDATION_MESSAGE =
  'Descreva o que você quer aprender antes de continuar.'
const START_PLANNING_ERROR_MESSAGE =
  'Não foi possível iniciar o planejamento agora. Tente novamente.'

export function usePlanningIntentComposer() {
  const { navigateToPlanner } = useNavigation()
  const { error: startPlanningError, isPending, startPlanning } = useStartPlanningAction()
  // The refusal lasts until the next mutate; the server refusal wins over an older reading.
  const hasQuotaRefusal = isPlanningQuotaExhaustedError(startPlanningError)
  const { isAiQuotaBlocked, getAiQuotaBlockedMessage, aiQuotaBlockedRole } =
    useAiQuotaBlock(hasQuotaRefusal)
  const [intent, setIntent] = useState('')
  const [validationMessage, setValidationMessage] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleIntentChange(value: string) {
    setIntent(value)
    if (validationMessage) setValidationMessage(null)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isAiQuotaBlocked) return
    const trimmedIntent = intent.trim()

    if (!trimmedIntent) {
      setValidationMessage(EMPTY_INTENT_VALIDATION_MESSAGE)
      textareaRef.current?.focus()
      return
    }

    startPlanning(trimmedIntent, {
      onSuccess: (session) => {
        // The planner page only resumes plannings opened from this composer (JN-12).
        registerPlanningEntry(session.id)
        navigateToPlanner(session.id)
      },
    })
  }

  return {
    intent,
    isPending,
    isAiQuotaBlocked,
    aiQuotaBlockedMessage: getAiQuotaBlockedMessage('home'),
    aiQuotaBlockedRole,
    // A quota refusal is explained by the blocked card, never by the generic error.
    startPlanningErrorMessage:
      startPlanningError && !hasQuotaRefusal ? START_PLANNING_ERROR_MESSAGE : null,
    textareaRef,
    validationMessage,
    handleIntentChange,
    handleSubmit,
  }
}
