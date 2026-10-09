import { Icon } from '@/ui/shared/widgets/components/icon'

export const EmptyState = ({ surface = 'page' }: { surface?: 'page' | 'fab' }) => (
  <div className='mx-auto my-auto max-w-md px-5 py-12 text-center'>
    <span
      className={`mx-auto grid place-items-center rounded-full bg-jade-tint text-jade-text ${surface === 'fab' ? 'size-11' : 'size-14'}`}
    >
      <Icon name='message-circle' className={surface === 'fab' ? 'size-5' : 'size-6'} />
    </span>
    <h2
      className={`font-serif font-normal ${surface === 'fab' ? 'mt-4 text-2xl' : 'mt-5 text-3xl'}`}
    >
      Como posso ajudar?
    </h2>
    <p className='mt-2 text-sm leading-6 text-muted-foreground'>
      Compartilhe uma dúvida para iniciar uma conversa com o Mentor.
    </p>
  </div>
)
