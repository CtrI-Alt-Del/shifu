import type { MentorResponseSnapshot } from '@/core/intelligence/mentor-response'
import { motion } from 'motion/react'
import type { MentorMessage } from '@/rest/services/intelligence-service'
import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { AnswerBlock } from './answer-block'
import { useMessageItem } from './use-message-item'
import { MentorAttachmentPreview } from '@/ui/intelligence/widgets/components/mentor-attachment-preview'
import { Sources } from './sources'

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
    attachments,
    handleOpenAttachment,
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
            <Sources sources={block.sources} onOpen={handleOpenAttachment} />
          </div>
        ))
      ) : isMentorMessage ? (
        <AnswerBlock content={message.content} />
      ) : (
        <p className='whitespace-pre-wrap'>{message.content}</p>
      )}
      {attachments.length > 0 ? (
        <ul aria-label='Arquivos desta mensagem' className='mt-3 space-y-3'>
          {attachments.map(({ attachment, url, error }) => (
            <li className='min-w-0 space-y-1' key={attachment.attachmentId}>
              {url && attachment.mediaType.startsWith('image/') ? (
                <MentorAttachmentPreview
                  filename={attachment.filename}
                  mediaType={attachment.mediaType}
                  src={url}
                />
              ) : null}
              <p className='break-all text-xs font-medium' title={attachment.filename}>
                {attachment.filename}
              </p>
              <p className='text-xs text-muted-foreground'>
                {attachment.mediaType.toUpperCase()}
                {' · '}
                {`${(attachment.sizeBytes / 1_000_000).toFixed(1).replace('.', ',')} MB`}
                {' · '}
                {attachment.status === 'partial'
                  ? 'Leitura parcial'
                  : attachment.status === 'ready'
                    ? 'Arquivo disponível'
                    : attachment.status === 'failed'
                      ? 'Arquivo não interpretado'
                      : 'Arquivo indisponível'}
              </p>
              {attachment.status === 'partial' ? (
                <p className='text-xs text-muted-foreground'>
                  {attachment.analyzedPages.length > 0
                    ? `Páginas analisadas: ${attachment.analyzedPages.join(', ')}.`
                    : 'Parte do conteúdo não pôde ser interpretada.'}
                  {attachment.illegiblePages.length > 0
                    ? ` Páginas ilegíveis: ${attachment.illegiblePages.join(', ')}.`
                    : ''}
                  {attachment.uninterpretedPages.length > 0
                    ? ` Páginas não analisadas: ${attachment.uninterpretedPages.join(', ')}.`
                    : ''}
                </p>
              ) : null}
              {attachment.mediaType.startsWith('image/') &&
              attachment.status !== 'failed' &&
              !url &&
              !error ? (
                <output className='block text-xs text-muted-foreground'>
                  Carregando prévia do arquivo…
                </output>
              ) : null}
              {error ? <output className='block'>{error}</output> : null}
            </li>
          ))}
        </ul>
      ) : null}
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
