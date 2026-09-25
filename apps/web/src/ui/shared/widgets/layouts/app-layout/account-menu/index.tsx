import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
import type { LayoutAccount } from '@/provision/auth/better-auth/better-auth-provider'

import { useAccountMenu } from './use-account-menu'

export type { LayoutAccount }

export type AccountMenuProps = {
  account: LayoutAccount
}

export const AccountMenu = ({ account }: AccountMenuProps) => {
  const {
    alertRef,
    errorMessage,
    handleSignOut,
    handleToggle,
    isOpen,
    menuId,
    menuRef,
    status,
    triggerId,
  } = useAccountMenu()

  return (
    <div className='relative shrink-0' ref={menuRef}>
      <Button
        aria-controls={menuId}
        aria-expanded={isOpen}
        aria-haspopup='menu'
        aria-label={isOpen ? 'Fechar menu da conta' : 'Abrir menu da conta'}
        className='size-8 min-h-8 rounded-full border border-white/10 px-0 text-muted-foreground hover:text-foreground'
        id={triggerId}
        onClick={handleToggle}
        type='button'
        variant='ghost'
      >
        <Icon name='user-circle' size={18} />
      </Button>

      {isOpen && (
        <div
          aria-label='Menu da conta'
          className='absolute right-0 top-full z-30 mt-2 w-[304px] max-w-[calc(100vw-2rem)] rounded-lg border border-border bg-card p-2 shadow-card'
          id={menuId}
          role='menu'
        >
          <div className='px-3 py-2'>
            <p className='truncate text-sm font-semibold text-foreground'>
              {account.displayName}
            </p>
            <p className='mt-0.5 break-all text-xs text-muted-foreground'>
              {account.email}
            </p>
          </div>

          <div aria-hidden='true' className='my-1 h-px bg-border' />

          <Button
            aria-disabled='true'
            className='w-full justify-start gap-3 px-3 text-sm font-normal text-muted-foreground disabled:cursor-default disabled:opacity-100'
            disabled
            role='menuitem'
            tabIndex={-1}
            type='button'
            variant='ghost'
          >
            <Icon name='user-circle' size={16} />
            <span>Sua conta</span>
          </Button>

          <div aria-hidden='true' className='my-1 h-px bg-border' />

          {errorMessage && (
            <div
              aria-live='assertive'
              className='mx-1 mb-1 flex items-start gap-2 rounded-md border border-selo-text bg-accent px-2 py-2 text-xs text-selo-text'
              ref={alertRef}
              role='alert'
              tabIndex={-1}
            >
              <Icon className='mt-0.5 shrink-0' name='circle-alert' size={15} />
              <span>{errorMessage} Pressione Sair para tentar novamente.</span>
            </div>
          )}

          {status === 'success' ? (
            <output
              aria-live='polite'
              className='flex items-center gap-2 rounded-md px-3 py-2 text-sm text-success'
            >
              <Icon name='circle-check' size={16} />
              <span>Saída concluída. Redirecionando para Entrar...</span>
            </output>
          ) : (
            <Button
              aria-busy={status === 'pending'}
              className='w-full justify-start gap-3 px-3 text-sm font-normal text-selo-text hover:bg-accent hover:text-selo-text'
              disabled={status === 'pending'}
              onClick={handleSignOut}
              role='menuitem'
              type='button'
              variant='ghost'
            >
              {status === 'pending' ? (
                <Icon className='animate-spin' name='loader-circle' size={16} />
              ) : (
                <Icon name='log-out' size={16} />
              )}
              <span>{status === 'pending' ? 'Saindo...' : 'Sair'}</span>
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
