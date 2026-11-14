import { createFileRoute } from '@tanstack/react-router'

import { GamificationCalendarPage } from '@/ui/gamification/widgets/pages/gamification-calendar-page'

export const Route = createFileRoute('/gamification/calendar/')({
  component: GamificationCalendarPage,
})
