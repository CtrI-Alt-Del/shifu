import { ConfirmationDialog } from '@/ui/shared/widgets/components/confirmation-dialog'

import { useRemoveSessionDialog } from './use-remove-session-dialog'

export const RemoveSessionDialog = () => {
  const {
    activeDialog,
    closeDialog,
    isRemovingSession,
    removalError,
    removeSession,
    session,
  } = useRemoveSessionDialog()

  return (
    <ConfirmationDialog
      cancelLabel='Manter conversa'
      confirmLabel='Excluir conversa'
      actionClassName='min-h-9! px-3! text-sm'
      description='O título e as mensagens desta conversa serão removidos permanentemente. Esta ação não pode ser desfeita.'
      error={removalError}
      icon='trash-2'
      isOpen={activeDialog === 'remove'}
      isSubmitting={isRemovingSession}
      itemName={session?.title}
      onCancel={closeDialog}
      onConfirm={() => void removeSession()}
      title='Excluir conversa?'
    />
  )
}
