import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export const useRemoveSessionDialog = () => {
  const mentor = useMentorContext()
  const session = mentor.sessionsPage.items.find(
    (item) => item.id === mentor.dialogSessionId,
  )
  return { ...mentor, session }
}
