import { createFileRoute } from '@tanstack/react-router'

import { GamificationOverviewPage } from '@/ui/gamification/widgets/pages/gamification-overview-page'

export const Route = createFileRoute('/gamification/overview/')({
  component: GamificationOverviewPage,
})
