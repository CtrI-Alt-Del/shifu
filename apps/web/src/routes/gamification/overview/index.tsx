import { createFileRoute } from '@tanstack/react-router'

import { EngagementPanelSection } from '@/ui/gamification/widgets/components/engagement-panel-section'
import { EngagementSummary } from '@/ui/gamification/widgets/components/engagement-summary'
import { LearningPanoramaSection } from '@/ui/learning/widgets/components/learning-panorama-section'
import { LearningPanoramaSummary } from '@/ui/learning/widgets/components/learning-panorama-summary'
import { ProgressPanelLayout } from '@/ui/shared/widgets/layouts/progress-panel-layout'

function ProgressPanelRoute() {
  return (
    <ProgressPanelLayout
      learningSummary={<LearningPanoramaSummary />}
      engagementSummary={<EngagementSummary />}
      learningSection={<LearningPanoramaSection />}
      engagementSection={<EngagementPanelSection />}
    />
  )
}

export const Route = createFileRoute('/gamification/overview/')({
  component: ProgressPanelRoute,
})
