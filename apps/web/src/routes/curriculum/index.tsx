import { createFileRoute } from '@tanstack/react-router'

import { CurriculumPage } from '@/ui/curriculum/widgets/pages/curriculum-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export const Route = createFileRoute('/curriculum/')({
  beforeLoad: () => requireAuthMiddleware(),
  component: CurriculumPage,
})
