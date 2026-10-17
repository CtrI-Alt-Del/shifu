import { Tabs, TabsContent } from '@/ui/shadcn/tabs'

import { AchievementsTabPanel } from './achievements-tab-panel'
import { CalendarTabPanel } from './calendar-tab-panel'
import type { GamificationTab } from './gamification-tabs'
import { GamificationTabs } from './gamification-tabs'
import { useGamificationPage } from './use-gamification-page'

export const GamificationPage = () => {
  const {
    familyGroups,
    historicalAchievements,
    profileSummary,
    state,
    isRetrying,
    activeTab,
    handleRetry,
    handleTabChange,
  } = useGamificationPage()

  return (
    <div className='mx-auto w-full max-w-7xl space-y-10'>
      <header className='space-y-2'>
        <h1 className='font-serif text-4xl'>Gamificação</h1>
        <p className='text-muted-foreground'>
          Sua constância, seus marcos e o XP que você conquistou.
        </p>
      </header>

      <Tabs
        onValueChange={(value) => handleTabChange(value as GamificationTab)}
        value={activeTab}
      >
        <GamificationTabs />

        <TabsContent className='pt-8' value='calendario'>
          <CalendarTabPanel />
        </TabsContent>

        <TabsContent className='pt-8' value='conquistas'>
          <AchievementsTabPanel
            familyGroups={familyGroups}
            historicalAchievements={historicalAchievements}
            isRetrying={isRetrying}
            onRetry={handleRetry}
            profileSummary={profileSummary}
            state={state}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
