import { createFileRoute } from '@tanstack/react-router'

import { IntelligencePage } from '@/ui/intelligence/widgets/pages/intelligence-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/intelligence/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: IntelligencePage,
})
