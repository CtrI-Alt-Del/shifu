import { createFileRoute } from '@tanstack/react-router'

import { LandingPage } from '@/ui/identity/widgets/pages/landing-page'
import { HomePage } from '@/ui/shared/widgets/pages/home-page'
import { enterMainPageMiddleware } from '@/middlewares/enter-main-page-middleware'

export const Route = createFileRoute('/')({
  beforeLoad: () => enterMainPageMiddleware(),
  component: RootPage,
})

function RootPage() {
  const entry = Route.useRouteContext()

  return entry.mode === 'public' ? <LandingPage /> : <HomePage />
}
