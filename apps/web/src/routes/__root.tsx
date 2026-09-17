import { createRootRoute } from '@tanstack/react-router'

import appCss from '@/ui/shared/styles/global.css?url'
import { RootLayout } from '@/ui/shared/widgets/layouts/root-layout'

export const Route = createRootRoute({
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
        title: 'Shifu — Aprendizagem guiada',
      },
    ],
    links: [
      {
        rel: 'stylesheet',
        href: appCss,
      },
      {
        rel: 'icon',
        href: '/favicon.svg',
        type: 'image/svg+xml',
      },
    ],
  }),
  shellComponent: RootLayout,
})
