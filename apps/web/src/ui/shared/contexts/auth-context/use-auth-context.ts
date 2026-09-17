import { useContext } from 'react'

import { AppError } from '@/core/errors/app-error'

import { AuthContext } from './index'

export function useAuthContext() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new AppError('useAuthContext deve ser usado dentro de AuthContextProvider.')
  }

  return context
}
