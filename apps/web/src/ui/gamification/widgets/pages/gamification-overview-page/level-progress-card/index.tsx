import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useLevelProgressCard } from './use-level-progress-card'

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
  const { formatXp, fillInitial, fillTransition } = useLevelProgressCard()

  return (
    <motion.article
      aria-labelledby='gamification-overview-level-title'
      className='flex flex-col justify-center gap-6 lg:pr-8'
      variants={ENTRANCE_SECTION}
    >
      <div className='flex flex-wrap items-center justify-between gap-4'>
        <h3
          className='font-serif text-[64px] leading-none text-latao-text'
          id='gamification-overview-level-title'
        >
          Nível {level}
        </h3>
        <p className='flex flex-col items-end gap-1'>
          <AnimatedNumber
            className='font-mono text-2xl font-medium'
            delay={0.2}
            format={(value) => `${formatXp(value)} XP`}
            value={totalXp}
          />
          <span className='text-[13px] text-muted-foreground'>acumulados</span>
        </p>
      </div>

      <div className='space-y-3'>
        <p className='text-lg font-medium'>
          <AnimatedNumber delay={0.35} format={formatXp} value={xpForNextLevel} /> XP para
          alcançar o nível {level + 1}
        </p>
        {/* The bar is decorative: the remaining XP and both thresholds are also
          rendered as text, so the fill is never the only carrier (RP-13). */}
        <div
          aria-label={`Progresso para o nível ${level + 1}`}
          aria-valuemax={100}
          aria-valuemin={0}
          aria-valuenow={levelPercentage}
          aria-valuetext={`${levelPercentage}% concluído, faltam ${formatXp(xpForNextLevel)} XP`}
          className='h-2 w-full overflow-hidden rounded-full bg-muted'
          role='progressbar'
        >
          <motion.div
            animate={{ width: `${levelPercentage}%` }}
            className='h-full rounded-full bg-latao-fill'
            initial={fillInitial}
            transition={fillTransition}
          />
        </div>
        <p className='flex justify-between gap-4 text-[13px] text-muted-foreground'>
          <span>
            Nível {level} · {formatXp(currentLevelXp)} XP
          </span>
          <span>
            Nível {level + 1} · {formatXp(nextLevelXp)} XP
          </span>
        </p>
      </div>

      <p className='flex gap-2 text-[13px] leading-normal text-muted-foreground'>
        <Icon className='mt-0.5 shrink-0' name='info' size={16} />
        XP reconhece sua prática. O domínio das Competências é acompanhado nas
        Habilidades.
      </p>
    </motion.article>
  )
}
