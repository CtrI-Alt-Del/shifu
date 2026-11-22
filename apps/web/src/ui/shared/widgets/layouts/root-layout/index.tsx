import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HeadContent, Scripts } from '@tanstack/react-router'
import { useState, type PropsWithChildren } from 'react'

import { Toaster } from '@/ui/shadcn/sonner'
import { RestContextProvider } from '@/ui/shared/contexts/rest-context'
import { AuthContextProvider } from '@/ui/shared/contexts/auth-context'
import { AppLayout } from '@/ui/shared/widgets/layouts/app-layout'

import { useRootLayout } from './use-root-layout'

export type RootLayoutProps = PropsWithChildren

export const RootLayout = ({ children }: RootLayoutProps) => {
  const { account, isHydrated, isPublic, mentorContextHint, theme } = useRootLayout()
  const [queryClient] = useState(() => new QueryClient())

  return (
    <html lang='pt-BR' data-theme={theme}>
      <head>
        <HeadContent />
      </head>
      <body data-hydrated={isHydrated}>
        <QueryClientProvider client={queryClient}>
          <RestContextProvider>
            <AuthContextProvider>
              {isPublic ? (
                children
              ) : (
                <AppLayout account={account} mentorContextHint={mentorContextHint}>
                  {children}
                </AppLayout>
              )}
            </AuthContextProvider>
          </RestContextProvider>
        </QueryClientProvider>
        <Toaster theme={theme} />
        <Scripts />
      </body>
    </html>
  )
}
