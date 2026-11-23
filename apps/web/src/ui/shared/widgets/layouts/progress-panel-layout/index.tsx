import type { ReactNode } from 'react'

export type ProgressPanelLayoutProps = {
  learningSummary: ReactNode
  engagementSummary: ReactNode
  learningSection: ReactNode
  engagementSection: ReactNode
}

// Each summary slot sits in its own two-column track, so the four cards form a
// single row on desktop and two stacked rows of two on mobile.
const SUMMARY_TRACK_CLASS_NAME = 'grid grid-cols-2 gap-3 sm:gap-4 lg:col-span-2'

export const ProgressPanelLayout = ({
  learningSummary,
  engagementSummary,
  learningSection,
  engagementSection,
}: ProgressPanelLayoutProps) => (
  <div className='flex flex-col gap-6'>
    <div className='grid grid-cols-1 gap-3 sm:gap-4 lg:grid-cols-4'>
      <div className={SUMMARY_TRACK_CLASS_NAME}>{learningSummary}</div>
      <div className={SUMMARY_TRACK_CLASS_NAME}>{engagementSummary}</div>
    </div>
    {learningSection}
    {engagementSection}
  </div>
)
