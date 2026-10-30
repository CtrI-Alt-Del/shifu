import { motion } from 'motion/react'
import { ENTRANCE_SECTION } from '@/constants/motion-variants'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'
import { SecurityForm } from './security-form'

export const AccountSecurityPage = () => {
  return (
    <MotionEntrance>
      <motion.div variants={ENTRANCE_SECTION}>
        <SecurityForm />
      </motion.div>
    </MotionEntrance>
  )
}
