import { createContext, type PropsWithChildren } from 'react'

import type { MentorContextValue } from './types'
import { useMentorContextProvider } from './use-mentor-context-provider'

export type MentorContextProviderProps = PropsWithChildren<{
  accountEmail: string
}>

export const MentorContext = createContext<MentorContextValue | null>(null)

const ScopedMentorContextProvider = ({
  accountEmail,
  children,
}: MentorContextProviderProps) => {
  const value = useMentorContextProvider(accountEmail)

  return <MentorContext.Provider value={value}>{children}</MentorContext.Provider>
}

export const MentorContextProvider = ({
  accountEmail,
  children,
}: MentorContextProviderProps) => (
  <ScopedMentorContextProvider accountEmail={accountEmail} key={accountEmail}>
    {children}
  </ScopedMentorContextProvider>
)
