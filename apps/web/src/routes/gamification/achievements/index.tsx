import { createFileRoute } from '@tanstack/react-router'

import { GamificationAchievementsPage } from '@/ui/gamification/widgets/pages/gamification-achievements-page'

export const Route = createFileRoute('/gamification/achievements/')({
  component: GamificationAchievementsPage,
})
