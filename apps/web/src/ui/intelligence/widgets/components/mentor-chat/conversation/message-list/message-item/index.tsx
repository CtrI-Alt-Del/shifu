import type { MentorMessage } from '@/rest/services/intelligence-service'

export type MessageItemProps = { message: MentorMessage; surface?: 'page' | 'fab' }

export const MessageItem = ({ message, surface = 'page' }: MessageItemProps) => (
  <li
    className={`max-w-[88%] whitespace-pre-wrap break-words px-4 py-3 ${surface === 'fab' ? 'rounded-xl text-sm' : 'rounded-2xl sm:max-w-[560px]'} ${message.role === 'learner' ? 'ml-auto bg-muted text-foreground' : 'bg-muted text-foreground'}`}
  >
    <p
      className={`mb-1 text-xs font-semibold ${message.role === 'mentor' && surface === 'fab' ? 'font-mono text-jade-text' : surface === 'fab' ? 'text-muted-foreground' : ''}`}
    >
      {message.role === 'learner' ? 'Você' : 'Mentor'}
    </p>
    <p>{message.content}</p>
    {message.role === 'learner' && message.inReplyToMessageId === null ? (
      <p className='mt-2 text-xs font-medium'>
        Mensagem salva. A resposta ainda não está disponível.
      </p>
    ) : null}
  </li>
)
