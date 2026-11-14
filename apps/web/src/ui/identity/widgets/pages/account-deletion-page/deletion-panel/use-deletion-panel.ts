import { useState } from 'react'

export function useDeletionPanel() {
  const [isOpen, setIsOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [hasConfirmed, setHasConfirmed] = useState(false)
  const [isPasswordVisible, setIsPasswordVisible] = useState(false)

  function handleOpenChange(open: boolean) {
    setIsOpen(open)
    if (!open) {
      setCurrentPassword('')
      setHasConfirmed(false)
      setIsPasswordVisible(false)
    }
  }

  function handleCurrentPasswordChange(password: string) {
    setCurrentPassword(password)
  }

  function handleConfirmationChange(checked: boolean) {
    setHasConfirmed(checked)
  }

  function handleTogglePasswordVisibility() {
    setIsPasswordVisible((visible) => !visible)
  }

  return {
    isOpen,
    currentPassword,
    hasConfirmed,
    isPasswordVisible,
    handleOpenChange,
    handleCurrentPasswordChange,
    handleConfirmationChange,
    handleTogglePasswordVisibility,
  }
}
