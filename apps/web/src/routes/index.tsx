import { createFileRoute } from '@tanstack/react-router'

import { HomePage } from '@/ui/shared/widgets/pages/home-page'
import { enterMainPageMiddleware } from '@/middlewares/enter-main-page-middleware'

export const Route = createFileRoute('/')({
  beforeLoad: () => enterMainPageMiddleware(),
  component: HomePage,
})
