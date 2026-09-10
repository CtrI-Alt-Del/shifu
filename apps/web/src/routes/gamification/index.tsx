import { createFileRoute } from '@tanstack/react-router'

import { GamificationPage } from '@/ui/gamification/widgets/pages/gamification-page'

export const Route = createFileRoute('/gamification/')({
  component: GamificationPage,
})
