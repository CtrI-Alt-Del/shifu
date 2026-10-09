import { MentorChat } from '@/ui/intelligence/widgets/components/mentor-chat'

import { useIntelligencePage } from './use-intelligence-page'

export const IntelligencePage = () => {
  const { isPageReady } = useIntelligencePage()

  if (!isPageReady) {
    return (
      <div className='sr-only' aria-live='polite'>
        Carregando conversa.
      </div>
    )
  }

  return <MentorChat surface='page' />
}
