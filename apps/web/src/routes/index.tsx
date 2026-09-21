import { createFileRoute } from '@tanstack/react-router'

import { DashboardPage } from '@/ui/shared/widgets/pages/dashboard-page'
import { enterMainPageMiddleware } from '@/middlewares/enter-main-page-middleware'

export const Route = createFileRoute('/')({
  beforeLoad: () => enterMainPageMiddleware(),
  component: DashboardPage,
})
