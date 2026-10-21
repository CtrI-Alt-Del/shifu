import type { Achievement } from '@/core/gamification/achievement'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type AchievementCardProps = {
  achievement: Achievement
}

const STATE_LABELS: Record<Achievement['state'], string> = {
  obtained: 'Conquistada',
  locked: 'Bloqueada',
  historical: 'Histórica',
}

export const AchievementCard = ({ achievement }: AchievementCardProps) => {
  const isLocked = achievement.state === 'locked'
  const isHistorical = achievement.state === 'historical'
  const hasProgress =
    achievement.progressCurrent !== null && achievement.progressTarget !== null

  return (
    <article
      className={`rounded-2xl border border-border bg-card p-6 shadow-card ${isLocked || isHistorical ? 'opacity-65' : ''}`}
    >
      <span
        className={`grid size-12 place-items-center rounded-2xl ${isLocked ? 'bg-muted text-muted-foreground' : 'bg-latao-tint text-latao-solid'}`}
      >
        <Icon name={isLocked ? 'lock-keyhole' : 'trophy'} size={20} />
      </span>
      <h3 className='mt-5 font-serif text-xl font-bold'>{achievement.name}</h3>
      {achievement.description ? (
        <p className='mt-2 text-sm leading-6 text-muted-foreground'>
          {achievement.description}
        </p>
      ) : null}
      {isLocked ? (
        <p className='mt-5 text-sm text-muted-foreground'>
          {achievement.criterionLabel}
          {hasProgress ? (
            <span className='ml-1 font-semibold text-foreground'>
              ({achievement.progressCurrent} de {achievement.progressTarget})
            </span>
          ) : null}
        </p>
      ) : null}
      <p
        className={`mt-5 text-xs font-bold uppercase tracking-[0.12em] ${achievement.state === 'obtained' ? 'text-latao-solid' : 'text-muted-foreground'}`}
      >
        {STATE_LABELS[achievement.state]}
        {!isLocked && achievement.unlockedAt
          ? ` em ${new Date(achievement.unlockedAt).toLocaleDateString('pt-BR')}`
          : ''}
      </p>
    </article>
  )
}
