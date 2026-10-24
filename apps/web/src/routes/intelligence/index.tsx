import { createFileRoute } from '@tanstack/react-router'

import { IntelligencePage } from '@/ui/intelligence/widgets/pages/intelligence-page'
import { requireAuthMiddleware } from '@/middlewares/require-auth-middleware'

const ULID_PATTERN = /^[0-7][0-9A-HJKMNP-TV-Z]{25}$/

function parseUlid(value: unknown) {
  return typeof value === 'string' && ULID_PATTERN.test(value) ? value : undefined
}

export function validateIntelligenceSearch(search: Record<string, unknown>) {
  return {
    session: parseUlid(search.session),
    message: parseUlid(search.message),
  }
}

export const Route = createFileRoute('/intelligence/')({
  beforeLoad: () => requireAuthMiddleware(),
  validateSearch: validateIntelligenceSearch,
  component: IntelligencePage,
})
