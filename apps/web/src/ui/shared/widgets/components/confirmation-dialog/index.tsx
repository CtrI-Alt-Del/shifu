import type { ReactNode, RefObject } from 'react'

import { Button } from '@/ui/shadcn/button'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/ui/shadcn/alert-dialog'
import { Icon, type IconName } from '@/ui/shared/widgets/components/icon'

export type ConfirmationDialogProps = {
  title: string
  itemName?: string
  description: string
  confirmLabel: string
  cancelLabel: string
  icon: IconName
  isOpen: boolean
  isSubmitting: boolean
  error?: string | null
  losses?: readonly string[]
  restoreFocusRef?: RefObject<HTMLElement | null>
  onConfirm: () => void
  onCancel: () => void
}

export const ConfirmationDialog = ({
  title,
  itemName,
  description,
  confirmLabel,
  cancelLabel,
  icon,
  isOpen,
  isSubmitting,
  error = null,
  losses = [],
  restoreFocusRef,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps): ReactNode => {
  return (
    <AlertDialog open={isOpen} onOpenChange={onCancel}>
      <AlertDialogContent
        onCloseAutoFocus={(event) => {
          if (!restoreFocusRef?.current) return
          event.preventDefault()
          restoreFocusRef.current.focus()
        }}
      >
        <button
          type='button'
          aria-label='Fechar'
          onClick={onCancel}
          disabled={isSubmitting}
          className='absolute right-4 top-4 rounded-md p-1 text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50'
        >
          <Icon name='x' className='h-4 w-4' />
        </button>
        <AlertDialogHeader>
          <div className='flex items-start gap-3 pr-8'>
            <div className='flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-accent'>
              <Icon name={icon} className='h-5 w-5 text-selo-text' />
            </div>
            <div className='flex flex-col gap-1'>
              <AlertDialogTitle>{title}</AlertDialogTitle>
              {itemName && (
                <p className='text-sm font-semibold text-foreground'>{itemName}</p>
              )}
              <AlertDialogDescription>{description}</AlertDialogDescription>
              {losses.length > 0 ? (
                <ul className='mt-3 space-y-2 text-left text-sm text-secondary-foreground'>
                  {losses.map((loss) => (
                    <li className='flex gap-2' key={loss}>
                      <Icon className='mt-0.5 h-4 w-4 shrink-0 text-selo-text' name='x' />
                      <span>{loss}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              <p className='text-sm font-medium text-selo-text'>
                Esta ação não pode ser desfeita.
              </p>
            </div>
          </div>
          {error && (
            <div className='mt-2 text-sm text-destructive' role='alert'>
              {error}
            </div>
          )}
        </AlertDialogHeader>
        <div className='border-t border-border' />
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isSubmitting}>{cancelLabel}</AlertDialogCancel>
          <Button variant='danger' onClick={onConfirm} disabled={isSubmitting}>
            {confirmLabel}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
