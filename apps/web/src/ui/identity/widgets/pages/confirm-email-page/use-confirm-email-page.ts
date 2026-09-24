import { useEffect, useRef, useState } from 'react'

import { useConfirmEmailAction } from '@/ui/identity/hooks/use-confirm-email-action'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type ConfirmEmailPageResult =
  | 'loading'
  | 'activated'
  | 'expired'
  | 'used'
  | 'invalid'
  | 'unavailable'

export type ConfirmEmailPageContent = {
  description: string
  success: boolean
  title: string
}

export function useConfirmEmailPage(token: string | undefined) {
  const { confirmEmail } = useConfirmEmailAction()
  const { navigateTo } = useNavigation()
  const initialToken = useRef(token).current
  const [result, setResult] = useState<ConfirmEmailPageResult>('loading')
  const [redirectTo, setRedirectTo] = useState<'root' | 'login'>('login')
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    window.history.replaceState({}, '', '/confirm-email')
    if (!initialToken || !/^[A-Za-z0-9_-]{43}$/.test(initialToken)) {
      setResult('invalid')
      return
    }
    let isCurrent = true
    void confirmEmail(initialToken)
      .then((response) => {
        if (!isCurrent) return
        setResult(response.result)
        setRedirectTo(response.redirectTo === 'root' ? 'root' : 'login')
      })
      .catch(() => {
        if (isCurrent) setResult('unavailable')
      })
    return () => {
      isCurrent = false
    }
  }, [confirmEmail, initialToken])

  useEffect(() => {
    if (result !== 'loading') headingRef.current?.focus()
  }, [result])

  async function handleContinue() {
    await navigateTo(redirectTo)
  }

  return {
    content: getContent(result),
    handleContinue,
    headingRef,
    redirectTo,
    result,
  }
}

function getContent(result: ConfirmEmailPageResult): ConfirmEmailPageContent {
  if (result === 'activated') {
    return {
      description: 'Seu e-mail foi confirmado e sua conta está ativa.',
      success: true,
      title: 'Conta confirmada',
    }
  }
  if (result === 'expired') {
    return {
      description: 'Este link expirou. Entre para solicitar outro link de confirmação.',
      success: false,
      title: 'Link expirado',
    }
  }
  if (result === 'used') {
    return {
      description: 'Este link já foi utilizado. Entre para continuar.',
      success: false,
      title: 'Link já utilizado',
    }
  }
  if (result === 'unavailable') {
    return {
      description: 'Não foi possível confirmar agora. Tente entrar novamente.',
      success: false,
      title: 'Não foi possível confirmar',
    }
  }
  if (result === 'loading') {
    return {
      description: 'Estamos verificando seu link de confirmação.',
      success: false,
      title: 'Confirmando e-mail',
    }
  }
  return {
    description: 'Este link não é válido. Entre para continuar.',
    success: false,
    title: 'Link inválido',
  }
}
