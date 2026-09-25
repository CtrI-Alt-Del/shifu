import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HeadContent, Scripts } from '@tanstack/react-router'
import { useState, type PropsWithChildren } from 'react'

import { RestContextProvider } from '@/ui/shared/contexts/rest-context'
import { AuthContextProvider } from '@/ui/shared/contexts/auth-context'
import { SquareBackground } from '@/ui/shared/widgets/components/square-background'
import { AppLayout } from '@/ui/shared/widgets/layouts/app-layout'

import { useRootLayout } from './use-root-layout'

export type RootLayoutProps = PropsWithChildren

export const RootLayout = ({ children }: RootLayoutProps) => {
  const { account, isPublic } = useRootLayout()
  const [queryClient] = useState(() => new QueryClient())

  return (
    <html lang='pt-BR'>
      <head>
        <HeadContent />
      </head>
      <body>
        <QueryClientProvider client={queryClient}>
          <RestContextProvider>
            <AuthContextProvider>
              <SquareBackground />
              {isPublic ? children : <AppLayout account={account}>{children}</AppLayout>}
            </AuthContextProvider>
          </RestContextProvider>
        </QueryClientProvider>
        <Scripts />
      </body>
    </html>
  )
}
