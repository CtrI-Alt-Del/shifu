import { GoalsListSection } from '@/ui/learning/widgets/layouts/goals-list-section'
import { PlanningIntentComposer } from '@/ui/intelligence/widgets/layouts/planning-intent-composer'

export const HomePage = () => {
  return (
    <div className='mx-auto w-full max-w-7xl space-y-8'>
      <PlanningIntentComposer />
      <GoalsListSection />
    </div>
  )
}
