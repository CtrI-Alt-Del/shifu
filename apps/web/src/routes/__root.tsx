/// <reference types="vite/client" />
import type { QueryClient } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import {
  HeadContent,
  Outlet,
  Scripts,
  createRootRouteWithContext,
} from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { Header } from '@/ui/global/widgets/header'
import { Toaster } from '@/ui/shadcn/components/sonner'
import globalCss from '@/ui/global/styles/global.css?url'

export const Route = createRootRouteWithContext<{
  queryClient: QueryClient
}>()({
  head: () => ({
    meta: [
      {
        charSet: 'utf-8',
      },
      {
        name: 'viewport',
        content: 'width=device-width, initial-scale=1',
      },
      {
        title: 'Shifu 🥋 | Assistente Virtual para Desenvolvimento de Habilidades',
      },
      {
        name: 'description',
        content:
          'Mentor no desenvolvimento de habilidades com diagnóstico real, jornada personalizada e prática guiada.',
      },
    ],
    links: [
      { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
      {
        rel: 'preconnect',
        href: 'https://fonts.gstatic.com',
        crossOrigin: 'anonymous',
      },
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&family=Oswald:wght@600&display=swap',
      },
      { rel: 'stylesheet', href: globalCss },
    ],
  }),
  component: RootComponent,
})

function RootComponent() {
  return (
    <html lang='pt-BR' className='dark'>
      <head>
        <HeadContent />
      </head>
      <body className='min-h-screen bg-page text-text-primary flex flex-col font-sans'>
        <Header />
        <main className='flex-1'>
          <Outlet />
        </main>
        <Toaster />
        <TanStackRouterDevtools position='bottom-right' />
        <ReactQueryDevtools buttonPosition='bottom-left' />
        <Scripts />
      </body>
    </html>
  )
}
