import type { MentorContextHint } from '@/core/intelligence/mentor-response'
import { createContext, type PropsWithChildren } from 'react'

import type { MentorContextValue } from './types'
import { useMentorContextProvider } from './use-mentor-context-provider'

export type MentorContextProviderProps = PropsWithChildren<{
  contextHint?: MentorContextHint | null
  accountEmail: string
}>

export const MentorContext = createContext<MentorContextValue | null>(null)

const ScopedMentorContextProvider = ({
  accountEmail,
  contextHint,
  children,
}: MentorContextProviderProps) => {
  const value = useMentorContextProvider(accountEmail, contextHint)

  return <MentorContext.Provider value={value}>{children}</MentorContext.Provider>
}

export const MentorContextProvider = ({
  accountEmail,
  contextHint,
  children,
}: MentorContextProviderProps) => (
  <ScopedMentorContextProvider
    accountEmail={accountEmail}
    contextHint={contextHint}
    key={accountEmail}
  >
    {children}
  </ScopedMentorContextProvider>
)
