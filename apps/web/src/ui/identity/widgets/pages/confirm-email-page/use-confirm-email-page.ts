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

  return { handleContinue, headingRef, result, redirectTo }
}
