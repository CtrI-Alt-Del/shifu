import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import type { ResetPasswordPageResult } from '../use-reset-password-page'

export type ResetPasswordLinkOutcomeProps = {
  headingRef: React.RefObject<HTMLHeadingElement | null>
  message: string | null
  onContinue: () => void
  onRetry: () => void
  onRequestNewLink: () => void
  requiresEmailConfirmation: boolean
  result: Exclude<ResetPasswordPageResult, 'form'>
}

export const ResetPasswordLinkOutcome = ({
  headingRef,
  message,
  onContinue,
  onRetry,
  onRequestNewLink,
  requiresEmailConfirmation,
  result,
}: ResetPasswordLinkOutcomeProps) => {
  const isSuccess = result === 'reset'
  const isUnavailable = result === 'unavailable'
  const isResolving = result === 'resolving'
  const title = isSuccess
    ? 'Senha redefinida'
    : isResolving
      ? 'Verificando link'
      : isUnavailable
        ? 'Não foi possível redefinir agora'
        : result === 'expired'
          ? 'Link expirado'
          : result === 'used'
            ? 'Link já utilizado'
            : 'Link inválido'
  const description = isSuccess
    ? requiresEmailConfirmation
      ? 'Sua senha foi atualizada. Confirme seu e-mail antes de entrar no restante do Shifu.'
      : 'Sua senha foi atualizada. Todas as sessões anteriores foram encerradas por segurança.'
    : isResolving
      ? 'Aguarde enquanto verificamos este link de recuperação.'
      : isUnavailable
        ? 'Tente novamente em alguns instantes. Sua senha não foi alterada.'
        : result === 'expired'
          ? 'Este link não pode mais ser usado. Solicite um novo link de recuperação.'
          : result === 'used'
            ? 'Este link já foi usado. Solicite um novo link ou entre com sua senha.'
            : 'Este link não é válido. Solicite um novo link ou entre no Shifu.'

  return (
    <section className='flex flex-col items-center text-center'>
      <Icon
        className={isSuccess ? 'text-success' : 'text-selo-text'}
        name={isSuccess ? 'circle-check' : 'circle-alert'}
        size={32}
      />
      <h2
        className='mt-5 font-serif text-2xl font-normal text-foreground'
        ref={headingRef}
        tabIndex={-1}
      >
        {title}
      </h2>
      <p className='mt-3 text-muted-foreground'>{description}</p>
      {message && (
        <p aria-live='assertive' className='mt-5 text-sm text-selo-text' role='alert'>
          {message}
        </p>
      )}
      {isResolving ? null : isSuccess ? (
        <Button className='mt-8 w-full' onClick={onContinue} type='button'>
          Entrar
        </Button>
      ) : isUnavailable ? (
        <Button className='mt-8 w-full' onClick={onRetry} type='button'>
          Tentar novamente
        </Button>
      ) : (
        <Button className='mt-8 w-full' onClick={onRequestNewLink} type='button'>
          Solicitar novo link
        </Button>
      )}
    </section>
  )
}
