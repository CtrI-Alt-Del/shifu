import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import { motion } from 'motion/react'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { AnswerBlock } from './answer-block'
import { useMessageItem } from './use-message-item'

export type MessageItemProps = {
  message: MentorMessage
  surface?: 'page' | 'fab'
  response?: MentorResponseSnapshot | null
}
export const MessageItem = ({
  message,
  surface = 'page',
  response,
}: MessageItemProps) => {
  const {
    blocks,
    shouldAnimateEntrance,
    shouldReduceMotion,
    copyAccessibleLabel,
    copyContent,
    copyError,
    copyIconName,
    copyLabel,
    hasResponse,
    isCopied,
    isLearnerMessage,
    isMentorMessage,
    speakerLabel,
    timeLabel,
    handleCopyMessage,
  } = useMessageItem(message, response)

  return (
    <motion.li
      initial={
        shouldAnimateEntrance && !shouldReduceMotion ? { opacity: 0.6, y: 6 } : false
      }
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0 : 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={`min-w-0 max-w-[88%] break-words px-4 py-3 ${surface === 'fab' ? 'rounded-xl text-sm' : 'rounded-2xl sm:max-w-[560px]'} ${isLearnerMessage ? 'ml-auto bg-muted text-foreground' : `border border-border text-foreground ${surface === 'fab' ? 'bg-muted' : 'bg-card'}`}`}
    >
      {speakerLabel ? (
        <p
          className={`mb-2 text-xs font-semibold ${surface === 'fab' ? 'font-mono text-jade-text' : ''}`}
        >
          {speakerLabel}
        </p>
      ) : null}
      {hasResponse ? (
        blocks.map((block) => (
          <div key={block.blockKey} className='mb-4'>
            {block.isTyping ? (
              <>
                <span className='sr-only'>{block.content}</span>
                <div aria-hidden='true'>
                  <AnswerBlock content={block.displayedContent} />
                </div>
              </>
            ) : (
              <AnswerBlock content={block.content} />
            )}
          </div>
        ))
      ) : isMentorMessage ? (
        <AnswerBlock content={message.content} />
      ) : (
        <p className='whitespace-pre-wrap'>{message.content}</p>
      )}
      <div className='mt-3 flex items-center justify-between gap-2 text-xs text-muted-foreground'>
        {timeLabel ? <time dateTime={message.createdAt}>{timeLabel}</time> : <span />}
        <Button
          aria-label={copyAccessibleLabel}
          className='shrink-0 gap-1.5 px-2 text-foreground'
          disabled={!copyContent}
          onClick={handleCopyMessage}
          title={copyAccessibleLabel}
          variant='ghost'
        >
          <Icon className='size-4' name={copyIconName} />
          <span>{copyLabel}</span>
        </Button>
      </div>
      {isCopied ? (
        <span aria-live='polite' className='sr-only'>
          Mensagem copiada
        </span>
      ) : null}
      {copyError ? (
        <output className='sr-only'>Não foi possível copiar a mensagem.</output>
      ) : null}
    </motion.li>
  )
}
