import { motion } from 'motion/react'

import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { AnimatedNumber } from '@/ui/shared/widgets/components/animated-number'

import type { ReviewView } from '../use-skill-completion'

export type SkillReviewPracticeProps = {
  review: ReviewView
}

export const SkillReviewPractice = ({ review }: SkillReviewPracticeProps) => {
  return (
    <motion.section
      aria-labelledby='skill-review-practice-title'
      className='flex flex-col gap-3 rounded-xl border border-border bg-surface-alt p-6 lg:flex-row lg:items-center lg:justify-between lg:gap-6 lg:py-5'
      variants={ENTRANCE_SECTION}
    >
      <div className='flex flex-col gap-1'>
        <h2
          className='text-base font-semibold leading-[1.2] text-foreground'
          id='skill-review-practice-title'
        >
          {review.title}
        </h2>
        <p className='text-sm leading-[1.2] text-secondary-foreground'>{review.notice}</p>
      </div>
      {review.stats.length > 0 ? (
        <ul className='flex gap-8'>
          {review.stats.map((stat) => (
            <li
              className='flex flex-col gap-0.5 lg:items-end lg:text-right'
              key={stat.id}
            >
              <strong className='font-mono text-xl font-semibold leading-[1.2] text-foreground'>
                <AnimatedNumber delay={0.3} value={stat.value} />
              </strong>
              <span className='text-[13px] leading-[1.2] text-muted-foreground'>
                {stat.label}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </motion.section>
  )
}
