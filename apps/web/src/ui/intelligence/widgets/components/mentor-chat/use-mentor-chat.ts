import { useMentorContext } from '@/ui/intelligence/hooks/use-mentor-context'

export type MentorChatSurface = 'page' | 'fab'

export const useMentorChat = (surface: MentorChatSurface) => {
  const mentor = useMentorContext()

  // IntelligencePage synchronizes shared selection with its URL.
  const handleSelectSession = async (sessionId: string) => {
    await mentor.selectSession(sessionId)
  }

  const handleStartNewConversation = () => {
    mentor.startNewConversation()
  }

  return { ...mentor, handleSelectSession, handleStartNewConversation, surface }
}
