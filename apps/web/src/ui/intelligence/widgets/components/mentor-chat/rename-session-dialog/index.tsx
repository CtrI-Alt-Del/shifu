import { Button } from '@/ui/shadcn/button'
import { Input } from '@/ui/shadcn/input'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/ui/shadcn/alert-dialog'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useRenameSessionDialog } from './use-rename-session-dialog'

export const RenameSessionDialog = () => {
  const {
    activeDialog,
    closeDialog,
    handleSubmit,
    isRenamingSession,
    renameError,
    session,
    setTitle,
    title,
    validationError,
  } = useRenameSessionDialog()

  return (
    <AlertDialog
      open={activeDialog === 'rename'}
      onOpenChange={(open) => !open && closeDialog()}
    >
      <AlertDialogContent>
        <button
          aria-label='Fechar'
          className='absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-white/5'
          disabled={isRenamingSession}
          onClick={closeDialog}
          type='button'
        >
          <Icon name='x' className='size-4' />
        </button>
        <AlertDialogHeader>
          <div className='flex items-start gap-3 pr-8'>
            <div className='grid size-11 shrink-0 place-items-center rounded-full bg-accent text-primary'>
              <Icon name='sparkles' />
            </div>
            <div>
              <AlertDialogTitle>Renomear conversa</AlertDialogTitle>
              <AlertDialogDescription>
                Escolha um título para encontrar esta conversa depois.
              </AlertDialogDescription>
            </div>
          </div>
        </AlertDialogHeader>
        <form className='space-y-2' onSubmit={handleSubmit}>
          <label className='block text-sm font-medium' htmlFor='mentor-session-title'>
            Título da conversa
          </label>
          <Input
            autoFocus
            id='mentor-session-title'
            onChange={(event) => setTitle(event.currentTarget.value)}
            value={title}
          />
          <p className='text-xs text-muted-foreground'>Até 120 caracteres.</p>
          {validationError || renameError ? (
            <p className='text-sm text-destructive' role='alert'>
              {validationError ?? renameError}
            </p>
          ) : null}
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isRenamingSession} onClick={closeDialog}>
              Cancelar
            </AlertDialogCancel>
            <Button disabled={isRenamingSession || !session} type='submit'>
              {isRenamingSession ? 'Salvando…' : 'Salvar'}
            </Button>
          </AlertDialogFooter>
        </form>
      </AlertDialogContent>
    </AlertDialog>
  )
}
