import { useId } from 'react'

import { Button } from '@/ui/shadcn/button'
import { Textarea } from '@/ui/shadcn/textarea'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { useComposer } from './use-composer'

export type ComposerProps = { surface?: 'page' | 'fab' }

export const Composer = ({ surface = 'fab' }: ComposerProps) => {
  const messageId = useId()
  const {
    canSend,
    draft,
    handleSubmit,
    hasAcceptedSession,
    isSubmittingFirstMessage,
    sendFirstMessage,
    setDraft,
    submissionError,
    textareaRef,
  } = useComposer()

  return (
    <form
      aria-label='Enviar primeira mensagem'
      aria-busy={isSubmittingFirstMessage}
      className={`shrink-0 space-y-2 ${surface === 'page' ? '' : 'border-t border-border bg-surface-alt p-6'}`}
      onSubmit={handleSubmit}
    >
      {hasAcceptedSession ? (
        <p className='mb-3 rounded-lg bg-muted p-3 text-sm text-muted-foreground'>
          Novas mensagens ainda não estão disponíveis nesta conversa.
        </p>
      ) : null}
      <label className='sr-only' htmlFor={messageId}>
        Escreva sua mensagem para o Mentor
      </label>
      {submissionError ? (
        <div
          className='mb-2 flex items-center justify-between gap-2 text-sm'
          role='alert'
        >
          <p>{submissionError}</p>
          <Button
            disabled={!draft.trim() || isSubmittingFirstMessage}
            onClick={() => void sendFirstMessage()}
            type='button'
            variant='ghost'
          >
            Tentar novamente
          </Button>
        </div>
      ) : null}
      <div className='flex min-h-14 items-end gap-2 rounded-md border border-control-border bg-muted px-2 py-1 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-selo-text'>
        <Button
          aria-label='Anexar arquivo ou imagem. Indisponível no momento'
          className={`h-11 w-11 shrink-0 gap-1.5 bg-white/5 px-2.5! text-sm font-medium! ${surface === 'page' ? 'sm:w-22' : ''}`}
          disabled
          title='Indisponível no momento'
          type='button'
          variant='ghost'
        >
          <Icon name='paperclip' className='size-4 shrink-0' />
          {surface === 'page' ? <span className='hidden sm:inline'>Anexar</span> : null}
        </Button>
        <Textarea
          className='min-h-11 min-w-0 max-h-44 flex-1 resize-none overflow-y-auto border-0! bg-transparent! px-0! py-3! text-sm focus-visible:border-transparent! focus-visible:ring-0! focus-visible:shadow-none! focus-visible:outline-none!'
          data-focus-ring='delegated'
          disabled={hasAcceptedSession || isSubmittingFirstMessage}
          id={messageId}
          onChange={(event) => setDraft(event.currentTarget.value)}
          placeholder='Pergunte ao Mentor…'
          ref={textareaRef}
          rows={1}
          value={draft}
        />
        <Button
          aria-label='Gravar ditado. Indisponível no momento'
          className='size-11 shrink-0 bg-white/5 px-0!'
          disabled
          title='Indisponível no momento'
          type='button'
          variant='ghost'
        >
          <Icon name='mic' className='size-4.5' />
        </Button>
        <Button
          aria-label={isSubmittingFirstMessage ? 'Enviando…' : 'Enviar'}
          className='size-11 shrink-0 px-0!'
          disabled={!canSend}
          type='submit'
        >
          <Icon
            name={isSubmittingFirstMessage ? 'loader-circle' : 'arrow-up'}
            className={`size-4.5 ${isSubmittingFirstMessage ? 'animate-spin motion-reduce:animate-none' : ''}`}
          />
        </Button>
      </div>
    </form>
  )
}
