import { GoalsListSection } from '@/ui/learning/widgets/layouts/goals-list-section'
import { PlanningIntentComposer } from '@/ui/intelligence/widgets/layouts/planning-intent-composer'

export const HomePage = () => {
  return (
    <div className='space-y-10'>
      <PlanningIntentComposer />
      <GoalsListSection />
    </div>
  )
}
