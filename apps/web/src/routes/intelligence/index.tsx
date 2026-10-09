import { createFileRoute } from '@tanstack/react-router'

import { IntelligencePage } from '@/ui/intelligence/widgets/pages/intelligence-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

export function validateIntelligenceSearch(search: Record<string, unknown>) {
  return {
    session:
      typeof search.session === 'string' &&
      /^[0-7][0-9A-HJKMNP-TV-Z]{25}$/.test(search.session)
        ? search.session
        : undefined,
  }
}

export const Route = createFileRoute('/intelligence/')({
  beforeLoad: () => requireAuthMiddleware(),
  validateSearch: validateIntelligenceSearch,
  component: IntelligencePage,
})
