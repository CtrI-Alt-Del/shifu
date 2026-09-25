import { useEffect, useId, useRef, useState } from 'react'

import { useAuthContext } from '@/ui/shared/contexts/auth-context/use-auth-context'
import { useNavigation } from '@/ui/shared/hooks/use-navigation'

export type AccountMenuStatus = 'idle' | 'pending' | 'success' | 'error'

export function useAccountMenu() {
  const { signOut } = useAuthContext()
  const { navigateTo } = useNavigation()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)
  const [status, setStatus] = useState<AccountMenuStatus>('idle')
  const isLogoutInFlightRef = useRef(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const alertRef = useRef<HTMLDivElement>(null)
  const instanceId = useId().replaceAll(':', '')
  const menuId = `account-menu-${instanceId}`
  const triggerId = `account-menu-trigger-${instanceId}`

  useEffect(() => {
    if (!isOpen || status === 'pending') return

    function handlePointerDown(event: PointerEvent) {
      if (!menuRef.current?.contains(event.target as Node)) setIsOpen(false)
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape') return

      event.preventDefault()
      setIsOpen(false)
      document.getElementById(triggerId)?.focus()
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, status, triggerId])

  useEffect(() => {
    if (status === 'error') alertRef.current?.focus()
  }, [status])

  function handleToggle() {
    if (status === 'pending') return

    setIsOpen((open) => !open)
  }

  async function handleSignOut() {
    if (isLogoutInFlightRef.current) return

    isLogoutInFlightRef.current = true
    setErrorMessage(null)
    setStatus('pending')

    try {
      await signOut()
      setStatus('success')
      await navigateTo('login')
    } catch {
      isLogoutInFlightRef.current = false
      setErrorMessage('Não foi possível sair agora. Tente novamente.')
      setStatus('error')
    }
  }

  return {
    alertRef,
    errorMessage,
    handleSignOut,
    handleToggle,
    isOpen,
    menuId,
    menuRef,
    status,
    triggerId,
  }
}
