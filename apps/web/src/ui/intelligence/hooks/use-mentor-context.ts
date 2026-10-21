import { useContext } from 'react'

import { AppError } from '@/core/errors/app-error'
import { MentorContext } from '@/ui/intelligence/contexts/mentor-context'

export const useMentorContext = () => {
  const context = useContext(MentorContext)
  if (!context) {
    throw new AppError('useMentorContext deve ser usado dentro de MentorContextProvider.')
  }
  return context
}
