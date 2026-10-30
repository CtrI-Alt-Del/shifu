import { motion } from 'motion/react'
import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'
import { DeletionPanel } from './deletion-panel'

export const AccountDeletionPage = () => {
  return (
    <MotionEntrance>
      <motion.div variants={ENTRANCE_SECTION}>
        <DeletionPanel />
      </motion.div>
    </MotionEntrance>
  )
}
