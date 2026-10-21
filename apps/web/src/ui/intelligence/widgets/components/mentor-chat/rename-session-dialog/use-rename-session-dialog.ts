import type { FormEvent } from 'react'
import { useEffect, useState } from 'react'

import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export const useRenameSessionDialog = () => {
  const mentor = useMentorContext()
  const session = mentor.sessionsPage.items.find(
    (item) => item.id === mentor.dialogSessionId,
  )
  const [title, setTitle] = useState(session?.title ?? '')
  const [validationError, setValidationError] = useState<string | null>(null)

  useEffect(() => {
    setTitle(session?.title ?? '')
    setValidationError(null)
  }, [session?.title])

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const normalized = title.trim()
    const count = Array.from(normalized).length
    if (count < 1 || count > 120) {
      setValidationError('Informe um título com até 120 caracteres.')
      return
    }
    setValidationError(null)
    void mentor.renameSession(normalized)
  }

  return { ...mentor, handleSubmit, session, setTitle, title, validationError }
}
