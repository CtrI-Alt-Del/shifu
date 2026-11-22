import { Link } from '@tanstack/react-router'
import { motion } from 'motion/react'

import { ENTRANCE_RISE, ENTRANCE_SECTION } from '@/constants/motion-variants'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { AddSkillCatalogSection } from '../../sections/add-skill-catalog-section'

export type GoalSkillAddPageProps = { goalId: string }

export const GoalSkillAddPage = ({ goalId }: GoalSkillAddPageProps) => {
  return (
    <main className='mx-auto w-full max-w-7xl pb-10'>
      <MotionEntrance className='flex flex-col gap-4 sm:gap-6'>
        <motion.div variants={ENTRANCE_RISE}>
          <Link
            className='inline-flex min-h-11 items-center gap-1 text-sm font-medium text-secondary-foreground transition-colors hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring'
            params={{ goalId }}
            to='/learning/goals/$goalId'
          >
            <span aria-hidden='true'>←</span> Voltar ao Objetivo
          </Link>
        </motion.div>
        <motion.h1
          className='font-serif text-[32px] font-normal leading-tight text-foreground sm:text-[40px]'
          variants={ENTRANCE_RISE}
        >
          Adicionar Habilidade
        </motion.h1>
        <motion.div variants={ENTRANCE_SECTION}>
          <AddSkillCatalogSection goalId={goalId} />
        </motion.div>
      </MotionEntrance>
    </main>
  )
}
