import { HeadContent, Scripts } from '@tanstack/react-router'
import type { PropsWithChildren } from 'react'

import { RestContextProvider } from '@/ui/shared/contexts/rest-context'
import { AuthContextProvider } from '@/ui/shared/contexts/auth-context'
import { SquareBackground } from '@/ui/shared/widgets/components/square-background'
import { AppLayout } from '@/ui/shared/widgets/layouts/app-layout'

import { useRootLayout } from './use-root-layout'

export type RootLayoutProps = PropsWithChildren

export const RootLayout = ({ children }: RootLayoutProps) => {
  const { isPublic } = useRootLayout()

  return (
    <html lang='pt-BR'>
      <head>
        <HeadContent />
      </head>
      <body>
        <RestContextProvider>
          <AuthContextProvider>
            <SquareBackground />
            {isPublic ? children : <AppLayout>{children}</AppLayout>}
          </AuthContextProvider>
        </RestContextProvider>
        <Scripts />
      </body>
    </html>
  )
}
