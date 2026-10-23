import { useFormatXp } from '@/ui/shared/hooks/use-format-xp'

export type LevelProgressCardProps = {
  level: number
  totalXp: number
  currentLevelXp: number
  nextLevelXp: number
  xpForNextLevel: number
  levelPercentage: number
}

export const LevelProgressCard = ({
  level,
  totalXp,
  currentLevelXp,
  nextLevelXp,
  xpForNextLevel,
  levelPercentage,
}: LevelProgressCardProps) => {
  const { formatXp } = useFormatXp()

  return (
    <article
      aria-labelledby='gamification-overview-level-title'
      className='rounded-3xl bg-latao-solid p-7 text-on-latao shadow-brand sm:p-9'
    >
      <h3
        className='text-sm font-bold uppercase tracking-[0.14em] text-on-latao/70'
        id='gamification-overview-level-title'
      >
        Seu nível
      </h3>

      <div className='mt-5 flex items-end gap-4'>
        <p className='font-serif text-6xl font-bold'>{String(level).padStart(2, '0')}</p>
        <p className='pb-2 text-lg'>{formatXp(totalXp)} XP acumulados</p>
      </div>

      {/* The bar is decorative: the percentage and both thresholds are also
        rendered as text, so the fill is never the only carrier (RP-13). */}
      <div
        aria-label={`Progresso para o nível ${level + 1}`}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={levelPercentage}
        aria-valuetext={`${levelPercentage}% concluído, faltam ${formatXp(xpForNextLevel)} XP`}
        className='mt-7 h-2 w-full overflow-hidden rounded-full bg-on-latao/25'
        role='progressbar'
      >
        <div
          className='h-full rounded-full bg-on-latao'
          style={{ width: `${levelPercentage}%` }}
        />
      </div>

      <div className='mt-3 flex justify-between text-sm text-on-latao/70'>
        <span>{formatXp(currentLevelXp)} XP</span>
        <span>{levelPercentage}%</span>
        <span>{formatXp(nextLevelXp)} XP</span>
      </div>

      <p className='mt-5 text-sm'>{formatXp(xpForNextLevel)} XP para o próximo nível</p>
    </article>
  )
}
