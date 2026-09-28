import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import type { ForgotPasswordPageStatus } from '../use-forgot-password-page'

export type ForgotPasswordRequestStatusProps = {
  isRetrying: boolean
  message: string | null
  onRetry: () => void
  onStartOver: () => void
  retryAfterSeconds: number | null
  status: ForgotPasswordPageStatus
  statusRef: React.RefObject<HTMLElement | null>
}

export const ForgotPasswordRequestStatus = ({
  isRetrying,
  message,
  onRetry,
  onStartOver,
  retryAfterSeconds,
  status,
  statusRef,
}: ForgotPasswordRequestStatusProps) => {
  const isLoading = status === 'loading'
  const isDeliveryIssue = status === 'delivery_issue'
  const title = isLoading
    ? 'Solicitação recebida'
    : isDeliveryIssue
      ? 'Não foi possível entregar o link'
      : 'Verifique seu e-mail'
  const description = isLoading
    ? 'Estamos atualizando o status de forma segura. Nenhuma conta é identificada nesta tela.'
    : isDeliveryIssue
      ? 'Você pode tentar uma nova solicitação. O resultado continua protegido por privacidade.'
      : 'Se o endereço for elegível, enviaremos um link para redefinir sua senha. O link vale por uma hora.'

  return (
    <section
      aria-labelledby='forgot-password-status-heading'
      aria-live='polite'
      className='flex flex-col items-center text-center'
      ref={statusRef}
      tabIndex={-1}
    >
      <Icon
        className={isDeliveryIssue ? 'text-selo-text' : 'text-success'}
        name={isDeliveryIssue ? 'circle-alert' : 'circle-check'}
        size={32}
      />
      <h2
        className='mt-5 font-serif text-2xl font-normal text-foreground'
        id='forgot-password-status-heading'
      >
        {title}
      </h2>
      <p className='mt-3 text-muted-foreground'>{description}</p>
      {status === 'cooldown' && retryAfterSeconds !== null && (
        <p className='mt-3 text-sm text-muted-foreground'>
          Aguarde {retryAfterSeconds}s antes de tentar novamente.
        </p>
      )}
      {message && (
        <p aria-live='assertive' className='mt-5 text-sm text-selo-text' role='alert'>
          {message}
        </p>
      )}
      {isDeliveryIssue && (
        <Button
          aria-busy={isRetrying}
          className='mt-8 w-full'
          disabled={isRetrying}
          onClick={onRetry}
          type='button'
        >
          {isRetrying ? 'Tentando novamente...' : 'Tentar novamente'}
        </Button>
      )}
      <Button
        className='mt-3 w-full'
        disabled={isRetrying}
        onClick={onStartOver}
        type='button'
        variant='ghost'
      >
        Usar outro e-mail
      </Button>
    </section>
  )
}
