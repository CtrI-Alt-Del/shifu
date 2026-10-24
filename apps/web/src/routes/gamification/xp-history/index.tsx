import { createFileRoute } from '@tanstack/react-router'

import { GamificationXpHistoryPage } from '@/ui/gamification/widgets/pages/gamification-xp-history-page'

export const Route = createFileRoute('/gamification/xp-history/')({
  component: GamificationXpHistoryPage,
})
