import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

export type MentorChatHeaderProps = {
  isDraft?: boolean
  title: string
  surface: 'page' | 'fab'
  onNewConversation: () => void
  onShowHistory: () => void
  onShowConversation: () => void
  onClose: () => void
  onExpand: () => void
  isHistoryVisible: boolean
  onRename?: () => void
}

export const MentorChatHeader = ({
  title,
  isDraft = false,
  surface,
  onShowHistory,
  onShowConversation,
  onClose,
  onExpand,
  isHistoryVisible,
  onRename,
}: MentorChatHeaderProps) => {
  if (surface === 'fab') {
    return (
      <header
        className={`shrink-0 border-b border-border px-6 py-5 ${!isHistoryVisible && isDraft ? 'min-h-26' : 'min-h-19'}`}
      >
        <div className='flex items-center gap-2'>
          {isHistoryVisible || !isDraft ? (
            <Button
              aria-label={
                isHistoryVisible ? 'Voltar à conversa' : 'Histórico de conversas'
              }
              className='size-11 shrink-0 p-0!'
              onClick={isHistoryVisible ? onShowConversation : onShowHistory}
              variant='ghost'
            >
              <Icon name='arrow-left' className='size-4' />
            </Button>
          ) : null}
          <h1
            className={`min-w-0 flex-1 truncate font-serif font-normal ${isHistoryVisible || isDraft ? 'text-3xl' : 'text-2xl'}`}
          >
            {isHistoryVisible ? 'Conversas' : isDraft ? 'Mentor' : title}
          </h1>
          {!isHistoryVisible ? (
            <Button
              aria-label='Expandir conversa'
              className='min-w-11 shrink-0 gap-1.5 bg-muted! px-2! text-xs font-normal!'
              onClick={onExpand}
              variant='ghost'
            >
              <Icon name='expand' className='size-4' />
              <span className='hidden sm:inline'>Abrir conversa</span>
            </Button>
          ) : null}
          {!isHistoryVisible && isDraft ? (
            <Button
              aria-label='Histórico de conversas'
              className='min-w-11 shrink-0 gap-1.5 bg-muted! px-2! text-xs font-normal!'
              onClick={onShowHistory}
              variant='ghost'
            >
              <Icon name='history' className='size-4' />
              <span className='hidden sm:inline'>Conversas</span>
            </Button>
          ) : null}
          <Button
            aria-label='Fechar painel do Mentor'
            className='size-11 shrink-0 bg-muted! p-0!'
            onClick={onClose}
            variant='ghost'
          >
            <Icon name='x' className='size-4' />
          </Button>
        </div>
        {!isHistoryVisible && isDraft ? (
          <p className='mt-1 text-xs text-muted-foreground'>
            Ajuda para continuar aprendendo
          </p>
        ) : null}
      </header>
    )
  }
  return (
    <header
      className={`flex items-center justify-between gap-4 ${surface === 'page' ? 'min-h-14 flex-wrap px-0 py-2 sm:flex-nowrap' : 'min-h-16 border-b border-border px-4 py-3'}`}
    >
      <div className='min-w-0'>
        {surface === 'page' ? (
          <h1 className='truncate font-serif text-3xl font-normal'>{title}</h1>
        ) : null}
      </div>
      <div
        className={`flex shrink-0 items-center gap-1 ${surface === 'page' ? 'max-w-full flex-wrap' : ''}`}
      >
        {surface === 'page' ? (
          <>
            <Button
              aria-label='Histórico de conversas'
              className='px-3 sm:hidden'
              onClick={isHistoryVisible ? onShowConversation : onShowHistory}
              variant='ghost'
            >
              <Icon name='menu' className='size-5' />
            </Button>
            <Button
              aria-label='Cota de uso. Indisponível no momento'
              className='px-2! font-mono text-xs font-normal! disabled:opacity-100!'
              disabled
              title='Indisponível no momento'
              variant='ghost'
            >
              IA · indisponível
            </Button>
            <Button
              className='gap-2 px-2! text-sm font-normal! disabled:opacity-100!'
              disabled={!onRename}
              onClick={onRename}
              title={onRename ? 'Renomear conversa' : 'Indisponível em uma conversa nova'}
              variant='ghost'
            >
              <Icon name='pencil' className='size-4 shrink-0' />
              Renomear
            </Button>
            <Button
              aria-label='Memórias. Indisponível no momento'
              className='gap-2 px-2! text-sm font-normal! disabled:opacity-100!'
              disabled
              title='Indisponível no momento'
              variant='ghost'
            >
              <Icon name='brain' className='size-4 shrink-0' />
              Memórias
            </Button>
          </>
        ) : null}
      </div>
    </header>
  )
}
