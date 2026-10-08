import type { Achievement } from '@/core/gamification/achievement'

import { AchievementCard } from '../achievement-card'

export type HistoricalAchievementsSectionProps = {
  achievements: Achievement[]
}

export const HistoricalAchievementsSection = ({
  achievements,
}: HistoricalAchievementsSectionProps) => (
  <section aria-labelledby='achievement-family-historico'>
    <h2 className='font-serif text-2xl font-bold' id='achievement-family-historico'>
      Histórico
    </h2>
    <p className='mt-2 text-sm text-muted-foreground'>
      Conquistas retiradas do catálogo, visíveis apenas para quem já as obteve.
    </p>
    <div className='mt-5 grid gap-4 md:grid-cols-3'>
      {achievements.map((achievement) => (
        <AchievementCard achievement={achievement} key={achievement.code} />
      ))}
    </div>
  </section>
)
