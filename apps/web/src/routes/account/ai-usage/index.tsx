import { createFileRoute } from '@tanstack/react-router'

import { AiUsagePage } from '@/ui/intelligence/widgets/pages/ai-usage-page'

export const Route = createFileRoute('/account/ai-usage/')({
  component: AiUsagePage,
})
