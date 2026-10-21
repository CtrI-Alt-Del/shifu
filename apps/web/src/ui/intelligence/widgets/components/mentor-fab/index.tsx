import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { MentorChat } from '@/ui/intelligence/widgets/components/mentor-chat'

import { useMentorFab } from './use-mentor-fab'

export const MentorFab = ({ isMentorPage = false }: { isMentorPage?: boolean }) => {
  const { closePanel, handlePanelKeyDown, isPanelOpen, openPanel, panelRef, triggerRef } =
    useMentorFab(isMentorPage)

  if (isMentorPage) return null

  return (
    <>
      <Button
        hidden={isPanelOpen}
        aria-expanded={isPanelOpen}
        aria-label={isPanelOpen ? 'Fechar Mentor' : 'Abrir Mentor'}
        className={`fixed right-4 z-40 size-14 rounded-full p-0 shadow-card lg:right-6 ${isPanelOpen ? 'hidden!' : 'bottom-20 lg:bottom-6'}`}
        onClick={isPanelOpen ? closePanel : openPanel}
        ref={triggerRef}
      >
        <Icon name={isPanelOpen ? 'x' : 'sparkles'} className='size-6' />
      </Button>
      {isPanelOpen ? (
        <div className='mentor-fab-overlay fixed inset-0 z-30 bg-background sm:flex sm:items-end sm:justify-end sm:bg-black/55 sm:pb-6 sm:pl-6 sm:pr-6 sm:pt-6'>
          <div
            aria-label='Painel do Mentor'
            className='mentor-fab-panel h-full w-full bg-surface-alt shadow-card sm:h-[min(800px,calc(100vh-4rem))] sm:w-[min(566px,calc(100vw-3rem))] sm:overflow-hidden sm:rounded-2xl sm:border sm:border-control-border'
            role='dialog'
            aria-modal='true'
            onKeyDown={handlePanelKeyDown}
            ref={panelRef}
            tabIndex={-1}
          >
            <MentorChat surface='fab' />
          </div>
        </div>
      ) : null}
    </>
  )
}
