import type { Achievement, AchievementFamily } from '@/core/gamification/achievement'

import { AchievementCard } from '../achievement-card'

export type AchievementFamilySectionProps = {
  family: AchievementFamily
  achievements: Achievement[]
}

const FAMILY_LABELS: Record<AchievementFamily, string> = {
  diagnostico: 'Diagnóstico',
  dominio: 'Domínio',
  conclusao: 'Conclusão',
  sequencia: 'Sequência',
  nivel: 'Nível',
}

export const AchievementFamilySection = ({
  family,
  achievements,
}: AchievementFamilySectionProps) => (
  <section aria-labelledby={`achievement-family-${family}`}>
    <h2 className='font-serif text-2xl font-bold' id={`achievement-family-${family}`}>
      {FAMILY_LABELS[family]}
    </h2>
    <div className='mt-5 grid gap-4 md:grid-cols-3'>
      {achievements.map((achievement) => (
        <AchievementCard achievement={achievement} key={achievement.code} />
      ))}
    </div>
  </section>
)
