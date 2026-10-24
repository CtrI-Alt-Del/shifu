import { motion } from 'motion/react'

import { ENTRANCE_RISE } from '@/constants/motion-variants'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

import { MentorMascot } from './mentor-mascot'

// Runs its own entrance so it also greets each new conversation, not only the
// first page load.
export const EmptyState = ({ surface = 'page' }: { surface?: 'page' | 'fab' }) => (
  <MotionEntrance className='mx-auto my-auto max-w-md px-5 py-12 text-center'>
    <MentorMascot surface={surface} />
    <motion.h2
      className={`font-serif font-normal ${surface === 'fab' ? 'mt-4 text-2xl' : 'mt-5 text-3xl'}`}
      variants={ENTRANCE_RISE}
    >
      Como posso ajudar?
    </motion.h2>
    <motion.p
      className='mt-2 text-sm leading-6 text-muted-foreground'
      variants={ENTRANCE_RISE}
    >
      Compartilhe uma dúvida para iniciar uma conversa com o Mentor.
    </motion.p>
  </MotionEntrance>
)
