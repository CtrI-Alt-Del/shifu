import type { LearnerMemoryOrigin } from '@/core/intelligence/learner-memory'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type MemoryOriginListProps = {
  origins: LearnerMemoryOrigin[]
}

const ROW_CLASS_NAME =
  'flex min-h-11 items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm'

export const MemoryOriginList = ({ origins }: MemoryOriginListProps) => (
  <ul aria-label='Origem da memória' className='space-y-2'>
    {origins.map((origin) => (
      <li
        key={`${origin.sessionId}:${origin.messageId ?? 'deleted'}:${origin.declaredAt}`}
      >
        {origin.isAvailable ? (
          <Anchor
            className={`${ROW_CLASS_NAME} text-foreground hover:bg-white/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text`}
            route='intelligence'
            search={{
              session: origin.sessionId,
              message: origin.messageId ?? undefined,
            }}
          >
            <Icon
              name='message-circle'
              className='size-4 shrink-0 text-muted-foreground'
            />
            <span className='min-w-0 break-words'>
              {origin.conversationTitle ?? 'Conversa'}
            </span>
          </Anchor>
        ) : (
          <p className={`${ROW_CLASS_NAME} text-muted-foreground`}>
            <Icon name='lock' className='size-4 shrink-0' />
            <span>Conversa excluída</span>
          </p>
        )}
      </li>
    ))}
  </ul>
)
