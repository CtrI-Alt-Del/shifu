import { motion } from 'motion/react'

import { ENTRANCE_POP, ENTRANCE_RISE } from '@/constants/motion-variants'
import { MentorMascot } from '@/ui/intelligence/widgets/components/mentor-mascot'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { MotionEntrance } from '@/ui/shared/widgets/components/motion-entrance'

// Runs its own entrance so it also greets each new conversation, not only the
// first page load.
export const EmptyState = ({ surface = 'page' }: { surface?: 'page' | 'fab' }) => (
  <MotionEntrance className='mx-auto my-auto max-w-md px-5 py-2 text-center sm:py-12'>
    <MentorMascot
      className={`mx-auto ${surface === 'fab' ? 'size-28' : 'size-32 sm:size-40'}`}
      isAnimated
      fallback={
        <motion.span
          className={`mx-auto grid place-items-center rounded-full bg-jade-tint text-jade-text ${surface === 'fab' ? 'size-11' : 'size-14'}`}
          variants={ENTRANCE_POP}
        >
          <Icon
            name='message-circle'
            className={surface === 'fab' ? 'size-5' : 'size-6'}
          />
        </motion.span>
      }
    />
    <motion.h2
      className={`font-serif font-normal ${surface === 'fab' ? 'mt-4 text-2xl' : 'mt-4 text-3xl sm:mt-5'}`}
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
