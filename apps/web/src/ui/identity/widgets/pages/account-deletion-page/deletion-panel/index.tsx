import { PRIVACY_CONTACT_MAILTO } from '@/ui/identity/constants/privacy-contact'
import { Button } from '@/ui/shadcn/button'
import { Checkbox } from '@/ui/shadcn/checkbox'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
} from '@/ui/shadcn/dialog'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { useDeletionPanel } from './use-deletion-panel'

export const DeletionPanel = () => {
  const {
    isOpen,
    currentPassword,
    hasConfirmed,
    isPasswordVisible,
    handleOpenChange,
    handleCurrentPasswordChange,
    handleConfirmationChange,
    handleTogglePasswordVisibility,
  } = useDeletionPanel()

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <section
        aria-labelledby='account-deletion-title'
        className='flex flex-col gap-6 rounded-lg border border-border bg-card p-6 sm:flex-row sm:items-center sm:justify-between'
      >
        <div className='max-w-[65ch] space-y-3'>
          <h2 id='account-deletion-title' className='text-base font-semibold'>
            Excluir conta
          </h2>
          <p className='text-sm leading-6 text-muted-foreground'>
            A exclusão é definitiva. Quando estiver disponível, após o encerramento
            confirmado, seus acessos serão bloqueados imediatamente e os dados ativos da
            conta serão apagados em até 24 horas.
          </p>
          <p className='text-sm leading-6'>
            A exclusão de conta ainda não está disponível. Nenhuma alteração será feita.
          </p>
          <div className='flex flex-wrap gap-x-5 gap-y-1 text-sm'>
            <Anchor
              route='privacy'
              className='inline-flex min-h-11 items-center underline underline-offset-4'
            >
              Política de privacidade
            </Anchor>
            <a
              href={PRIVACY_CONTACT_MAILTO}
              className='inline-flex min-h-11 items-center underline underline-offset-4'
            >
              Solicitar atendimento
            </a>
          </div>
        </div>
        <DialogTrigger asChild>
          <Button
            type='button'
            variant='outline'
            className='shrink-0 gap-2 border-selo-text text-sm text-selo-text'
          >
            <Icon name='trash-2' size={16} />
            Excluir minha conta
          </Button>
        </DialogTrigger>
      </section>
      <DialogContent className='!w-[calc(100%-40px)] !max-w-[686px] max-h-[calc(100dvh-40px)] overflow-y-auto !rounded-[14px] !border-border !p-6 !shadow-none sm:!p-7'>
        <div className='mb-5 flex items-start gap-3 border-b border-border pb-5 pr-10'>
          <div className='flex size-11 shrink-0 items-center justify-center rounded-full bg-accent'>
            <Icon name='trash-2' size={20} className='text-selo-text' />
          </div>
          <div className='min-w-0 space-y-2'>
            <DialogTitle className='font-serif text-3xl'>Excluir sua conta?</DialogTitle>
            <DialogDescription className='text-sm leading-6 text-muted-foreground'>
              A exclusão é definitiva. Quando estiver disponível, após o encerramento
              confirmado, seus acessos serão bloqueados imediatamente e os dados ativos da
              conta serão apagados em até 24 horas, incluindo Objetivos, progresso,
              conversas e recompensas.
            </DialogDescription>
          </div>
        </div>
        <p className='mt-4 text-sm leading-6 text-muted-foreground'>
          Consulte os prazos de conservação e as exceções na{' '}
          <Anchor route='privacy' className='underline underline-offset-4'>
            Política de privacidade
          </Anchor>
          .
        </p>
        <p id='account-deletion-unavailable' className='mt-4 text-sm leading-6'>
          A exclusão de conta ainda não está disponível. Nenhuma alteração será feita.
        </p>
        <div className='mt-5 space-y-2'>
          <Label htmlFor='account-deletion-password'>Senha atual</Label>
          <div className='relative'>
            <Input
              id='account-deletion-password'
              type={isPasswordVisible ? 'text' : 'password'}
              autoComplete='off'
              value={currentPassword}
              onChange={(event) => handleCurrentPasswordChange(event.target.value)}
              className='min-h-[52px] pr-12'
            />
            <Button
              type='button'
              variant='ghost'
              aria-label={isPasswordVisible ? 'Ocultar senha' : 'Mostrar senha'}
              aria-pressed={isPasswordVisible}
              onClick={handleTogglePasswordVisibility}
              className='absolute right-1 top-1 !min-h-11 w-11 !px-0'
            >
              <Icon name={isPasswordVisible ? 'eye-off' : 'eye'} size={18} />
            </Button>
          </div>
        </div>
        <Checkbox
          checked={hasConfirmed}
          onCheckedChange={handleConfirmationChange}
          label='Entendo que isso é definitivo'
          className='mt-4 !border-0 !bg-transparent !px-0 text-sm'
        />
        <div className='mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end'>
          <DialogClose asChild>
            <Button type='button' variant='ghost' className='text-sm'>
              Cancelar
            </Button>
          </DialogClose>
          <Button
            type='button'
            variant='danger'
            disabled
            aria-describedby='account-deletion-unavailable'
            className='gap-2 text-sm'
          >
            <Icon name='trash-2' size={16} />
            Excluir definitivamente
          </Button>
        </div>
        <DialogClose asChild>
          <Button
            type='button'
            variant='ghost'
            aria-label='Fechar confirmação'
            className='absolute right-3 top-3 size-11 !px-0'
          >
            <Icon name='x' size={18} />
          </Button>
        </DialogClose>
      </DialogContent>
    </Dialog>
  )
}
