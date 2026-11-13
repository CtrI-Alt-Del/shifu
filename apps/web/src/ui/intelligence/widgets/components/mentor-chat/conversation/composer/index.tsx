import { useId, useRef } from 'react'

import { Button } from '@/ui/shadcn/button'
import { Textarea } from '@/ui/shadcn/textarea'
import { AiQuotaBlockedCard } from '@/ui/intelligence/widgets/components/ai-quota-blocked-card'
import { AiQuotaWarningCard } from '@/ui/intelligence/widgets/components/ai-quota-warning-card'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { AttachmentList } from './attachment-list'
import { DictationWave } from './dictation-wave'

import { useComposer } from './use-composer'

/**
 * The blocked composer frame already dims everything inside by half, so the paused ghost
 * buttons keep their own dimming off and use the opaque board fill.
 */
const BLOCKED_GHOST_BUTTON_CLASS_NAMES = {
  open: 'bg-white/5',
  blocked: 'bg-surface-alt! aria-disabled:opacity-100!',
} as const

export type ComposerProps = {
  surface?: 'page' | 'fab'
  /** Id of the blocked card, shared with the sibling controls that the quota blocks. */
  aiQuotaBlockedId?: string
}

export const Composer = ({ surface = 'fab', aiQuotaBlockedId }: ComposerProps) => {
  const messageId = useId()
  const ownAiQuotaBlockedId = useId()
  const blockedCardId = aiQuotaBlockedId ?? ownAiQuotaBlockedId
  const {
    canSend,
    canManageAttachments,
    dictationStatus,
    dictationError,
    dictationElapsedSeconds,
    dictationLanguageAvailability,
    dictationInstallationStatus,
    dictationInstallationError,
    isDictationBusy,
    canStartDictation,
    canInstallDictationLanguage,
    isActionBlocked,
    isAiQuotaBlocked,
    isAiQuotaNearLimit,
    aiQuotaBlockedMessage,
    aiQuotaBlockedRole,
    aiQuotaAccountId,
    aiQuotaPercentage,
    aiQuotaRenewsOn,
    isRefreshingActions,
    hasActionRefreshTimedOut,
    refreshActions,
    startDictation,
    finishDictation,
    cancelDictation,
    installDictationLanguage,
    draft,
    handleKeyDown,
    handleSubmit,
    isResponsePending,
    isSubmittingFirstMessage,
    placeholder,
    sendFirstMessage,
    setDraft,
    submissionError,
    textareaRef,
    draftAttachments = [],
    addAttachments = async () => {},
    retryAttachment = async () => {},
    removeAttachment = async () => {},
  } = useComposer(surface)
  const actionBlockId = useId()
  const attachmentInputId = useId()
  const attachmentInputRef = useRef<HTMLInputElement | null>(null)
  const attachButtonRef = useRef<HTMLButtonElement | null>(null)

  async function handleRemoveAttachment(localKey: string) {
    await removeAttachment(localKey)
    attachButtonRef.current?.focus()
  }

  return (
    <form
      aria-label='Enviar mensagem ao Mentor'
      aria-busy={isSubmittingFirstMessage}
      className={`shrink-0 space-y-2 ${surface === 'page' ? 'mx-4' : 'border-t border-border bg-surface-alt p-6'}`}
      onSubmit={handleSubmit}
    >
      {isAiQuotaBlocked ? (
        <AiQuotaBlockedCard
          id={blockedCardId}
          message={aiQuotaBlockedMessage}
          role={aiQuotaBlockedRole}
        />
      ) : isAiQuotaNearLimit &&
        aiQuotaAccountId &&
        aiQuotaRenewsOn &&
        aiQuotaPercentage !== null ? (
        <AiQuotaWarningCard
          accountId={aiQuotaAccountId}
          className='mb-3.5 sm:mb-[15px]'
          percentage={aiQuotaPercentage}
          renewsOn={aiQuotaRenewsOn}
        />
      ) : null}
      <label className='sr-only' htmlFor={messageId}>
        Escreva sua mensagem para o Mentor
      </label>
      {isDictationBusy || dictationStatus === 'review' ? (
        <div className='space-y-3 rounded-lg border border-border bg-surface p-4'>
          <output className='flex items-center justify-between gap-3' aria-live='polite'>
            <span className='text-sm font-medium'>
              {dictationStatus === 'preparing'
                ? 'Preparando ditado…'
                : dictationStatus === 'recording'
                  ? 'Gravando ditado…'
                  : dictationStatus === 'transcribing'
                    ? 'Transcrevendo ditado…'
                    : 'Revise seu ditado'}
            </span>
            {dictationStatus === 'recording' ? (
              <span className='flex items-center gap-2'>
                <DictationWave />
                <span className='text-sm tabular-nums'>
                  {String(Math.floor(dictationElapsedSeconds / 60)).padStart(2, '0')}:
                  {String(dictationElapsedSeconds % 60).padStart(2, '0')}
                </span>
              </span>
            ) : null}
          </output>
          {dictationStatus !== 'preparing' ? (
            <p className='text-sm text-muted-foreground'>
              {dictationStatus === 'recording'
                ? 'Fale sua mensagem. Ao encerrar, você poderá revisar o texto.'
                : dictationStatus === 'transcribing'
                  ? 'O texto ficará disponível para você revisar antes de enviar.'
                  : 'Edite o texto se precisar e toque em Enviar.'}
            </p>
          ) : null}
          {isDictationBusy ? (
            <div className='flex items-center justify-between gap-3'>
              <Button
                className='min-h-11'
                type='button'
                variant='ghost'
                onClick={cancelDictation}
              >
                Cancelar
              </Button>
              {dictationStatus === 'recording' ? (
                <Button className='min-h-11' type='button' onClick={finishDictation}>
                  Encerrar ditado
                </Button>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
      {dictationError || dictationInstallationError ? (
        <p role='alert' className='text-sm'>
          {dictationError || dictationInstallationError}
        </p>
      ) : null}
      {dictationInstallationStatus === 'installing' ? (
        <output aria-live='polite' className='block text-sm'>
          Instalando pacote de idioma…
        </output>
      ) : dictationInstallationStatus === 'installed' ? (
        <output aria-live='polite' className='block text-sm'>
          Pacote de idioma instalado. Você pode gravar seu ditado.
        </output>
      ) : null}
      {!isDictationBusy &&
      dictationLanguageAvailability &&
      dictationLanguageAvailability !== 'available' ? (
        <div className='space-y-2'>
          <output aria-live='polite' className='block text-xs text-muted-foreground'>
            {dictationLanguageAvailability === 'checking'
              ? 'Verificando disponibilidade do ditado…'
              : 'Ditado indisponível neste navegador. Continue digitando.'}
          </output>
          {canInstallDictationLanguage ? (
            <Button
              className='min-h-11'
              type='button'
              variant='ghost'
              disabled={dictationInstallationStatus === 'installing'}
              onClick={() => void installDictationLanguage(surface)}
            >
              Instalar pacote de idioma
            </Button>
          ) : null}
        </div>
      ) : null}
      {submissionError ? (
        <div
          className='mb-2 flex items-center justify-between gap-2 text-sm'
          role='alert'
        >
          <p>{submissionError}</p>
          <Button
            disabled={!canSend}
            onClick={() => void sendFirstMessage(surface)}
            type='button'
            variant='ghost'
          >
            Tentar novamente
          </Button>
        </div>
      ) : null}
      {isActionBlocked ? (
        isRefreshingActions ? (
          <output
            className='block px-1 text-sm text-secondary-foreground'
            id={actionBlockId}
          >
            Atualizando a conversa…
          </output>
        ) : hasActionRefreshTimedOut ? (
          <output
            className='flex flex-wrap items-center justify-between gap-2 px-1 text-sm text-secondary-foreground'
            id={actionBlockId}
          >
            <span>Ainda não foi possível atualizar a conversa.</span>
            <Button
              className='border border-control-border text-foreground'
              onClick={refreshActions}
              type='button'
              variant='ghost'
            >
              Tentar novamente
            </Button>
          </output>
        ) : (
          <p className='px-1 text-sm text-secondary-foreground' id={actionBlockId}>
            Confirme ou recuse a ação proposta para continuar.
          </p>
        )
      ) : null}
      <p className='px-1 text-xs text-muted-foreground'>
        Anexe até cinco arquivos PNG, JPG, WebP, PDF, JSON, CSV ou TXT. Cada arquivo pode
        ter até 2 MB. A mensagem de texto é opcional ao enviar arquivos.
      </p>
      <div
        className={`flex min-h-14 items-end gap-2 rounded-md border border-control-border px-2 py-1 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-selo-text ${isAiQuotaBlocked ? 'bg-card opacity-50' : 'bg-muted'}`}
      >
        <Button
          aria-controls={attachmentInputId}
          aria-describedby={isAiQuotaBlocked ? blockedCardId : undefined}
          aria-disabled={isAiQuotaBlocked || undefined}
          aria-label='Anexar arquivo ou imagem'
          className={`h-11 w-11 shrink-0 gap-1.5 px-2.5! text-sm font-medium! ${surface === 'page' ? 'sm:w-22' : ''} ${BLOCKED_GHOST_BUTTON_CLASS_NAMES[isAiQuotaBlocked ? 'blocked' : 'open']}`}
          disabled={!canManageAttachments && !isAiQuotaBlocked}
          onClick={
            isAiQuotaBlocked ? undefined : () => attachmentInputRef.current?.click()
          }
          ref={attachButtonRef}
          title='Anexar arquivo ou imagem'
          type='button'
          variant='ghost'
        >
          <Icon name='paperclip' className='size-4 shrink-0' />
          {surface === 'page' ? <span className='hidden sm:inline'>Anexar</span> : null}
        </Button>
        <Textarea
          aria-describedby={
            isAiQuotaBlocked ? blockedCardId : isActionBlocked ? actionBlockId : undefined
          }
          className={`min-h-11 min-w-0 max-h-44 flex-1 resize-none overflow-y-auto border-0! bg-transparent! px-0! py-3! text-sm focus-visible:border-transparent! focus-visible:ring-0! focus-visible:shadow-none! focus-visible:outline-none! ${isAiQuotaBlocked ? 'disabled:opacity-100!' : ''}`}
          data-focus-ring='delegated'
          disabled={
            isResponsePending ||
            isSubmittingFirstMessage ||
            isDictationBusy ||
            isActionBlocked ||
            isAiQuotaBlocked
          }
          id={messageId}
          onChange={(event) => setDraft(event.currentTarget.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          ref={textareaRef}
          rows={1}
          value={draft}
        />
        <Button
          aria-describedby={isAiQuotaBlocked ? blockedCardId : undefined}
          aria-disabled={isAiQuotaBlocked || undefined}
          aria-label={
            canStartDictation ? 'Gravar ditado' : 'Gravar ditado. Indisponível no momento'
          }
          className={`size-11 shrink-0 px-0! ${BLOCKED_GHOST_BUTTON_CLASS_NAMES[isAiQuotaBlocked ? 'blocked' : 'open']}`}
          disabled={!canStartDictation && !isAiQuotaBlocked}
          onClick={isAiQuotaBlocked ? undefined : () => void startDictation(surface)}
          title={canStartDictation ? 'Gravar ditado' : 'Indisponível no momento'}
          type='button'
          variant='ghost'
        >
          <Icon name='mic' className='size-4.5' />
        </Button>
        <Button
          aria-describedby={isAiQuotaBlocked ? blockedCardId : undefined}
          aria-disabled={isAiQuotaBlocked || undefined}
          aria-label={isSubmittingFirstMessage ? 'Enviando…' : 'Enviar'}
          className='size-11 shrink-0 px-0!'
          disabled={!canSend && !isAiQuotaBlocked}
          onClick={isAiQuotaBlocked ? (event) => event.preventDefault() : undefined}
          type='submit'
        >
          <Icon
            name={isSubmittingFirstMessage ? 'loader-circle' : 'arrow-up'}
            className={`size-4.5 ${isSubmittingFirstMessage ? 'animate-spin motion-reduce:animate-none' : ''}`}
          />
        </Button>
      </div>
      <input
        accept='.png,.jpg,.jpeg,.webp,.pdf,.json,.csv,.txt,image/png,image/jpeg,image/webp,application/pdf,application/json,text/csv,text/plain'
        aria-label='Selecionar arquivos PNG, JPG, WebP, PDF, JSON, CSV ou TXT'
        className='sr-only'
        id={attachmentInputId}
        multiple
        onChange={(event) => {
          const files = Array.from(event.currentTarget.files ?? [])
          event.currentTarget.value = ''
          void addAttachments(files)
        }}
        ref={attachmentInputRef}
        tabIndex={-1}
        type='file'
      />
      <AttachmentList
        attachments={draftAttachments}
        disabled={!canManageAttachments}
        onRemove={(localKey) => void handleRemoveAttachment(localKey)}
        onRetry={(localKey) => void retryAttachment(localKey)}
      />
    </form>
  )
}
