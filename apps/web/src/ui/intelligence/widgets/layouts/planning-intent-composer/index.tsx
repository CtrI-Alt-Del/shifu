import { AiQuotaBlockedCard } from '@/ui/intelligence/widgets/components/ai-quota-blocked-card'
import { Button } from '@/ui/shadcn/button'
import { Label } from '@/ui/shadcn/label'
import { Textarea } from '@/ui/shadcn/textarea'
import { BorderGlow } from '@/ui/shared/widgets/components/border-glow'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { usePlanningIntentComposer } from './use-planning-intent-composer'

const AI_QUOTA_BLOCKED_ID = 'planning-intent-ai-quota-blocked'

export const PlanningIntentComposer = () => {
  const {
    aiQuotaBlockedMessage,
    aiQuotaBlockedRole,
    handleIntentChange,
    handleSubmit,
    intent,
    isAiQuotaBlocked,
    isPending,
    startPlanningErrorMessage,
    textareaRef,
    validationMessage,
  } = usePlanningIntentComposer()

  const intentField = (
    <Textarea
      aria-describedby={
        isAiQuotaBlocked
          ? AI_QUOTA_BLOCKED_ID
          : validationMessage
            ? 'planning-intent-validation'
            : undefined
      }
      aria-invalid={Boolean(validationMessage)}
      data-focus-ring='delegated'
      disabled={isPending || isAiQuotaBlocked}
      id='planning-intent'
      className={`planning-intent-field__input px-4 py-3.5 text-base ${isAiQuotaBlocked ? 'resize-none disabled:opacity-100!' : ''}`}
      onChange={(event) => handleIntentChange(event.target.value)}
      placeholder='Ex.: quero conseguir automatizar tarefas repetitivas com Python'
      ref={textareaRef}
      rows={4}
      value={intent}
    />
  )

  return (
    <section>
      <h1 className='max-w-2xl font-serif text-4xl leading-tight tracking-tight'>
        O que você quer aprender?
      </h1>
      <p className='mt-1.5 max-w-3xl leading-relaxed text-foreground/80'>
        Descreva com suas palavras. O Shifu monta uma proposta com Habilidades reais e
        você confirma antes de criar.
      </p>

      <form className='mt-7' noValidate onSubmit={handleSubmit}>
        <Label className='sr-only' htmlFor='planning-intent'>
          O que você quer aprender?
        </Label>
        {isAiQuotaBlocked ? (
          // Quota blocked: a plain dimmed frame, with no animated glow around a dead field.
          <div className='rounded-md border border-control-border bg-card opacity-50'>
            {intentField}
          </div>
        ) : (
          <BorderGlow className='planning-intent-field'>{intentField}</BorderGlow>
        )}

        {validationMessage && (
          <p
            className='mt-2 flex items-center gap-2 text-sm text-foreground'
            id='planning-intent-validation'
            role='alert'
          >
            <Icon name='circle-alert' size={16} />
            {validationMessage}
          </p>
        )}

        {startPlanningErrorMessage && (
          <p
            className='mt-2 flex items-center gap-2 text-sm text-foreground'
            role='alert'
          >
            <Icon name='circle-alert' size={16} />
            {startPlanningErrorMessage}
          </p>
        )}

        {isAiQuotaBlocked && (
          <AiQuotaBlockedCard
            className='mt-3'
            id={AI_QUOTA_BLOCKED_ID}
            message={aiQuotaBlockedMessage}
            role={aiQuotaBlockedRole}
          />
        )}

        <div className='mt-3 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between'>
          <Anchor
            className='inline-flex min-h-11 items-center justify-center rounded-md px-3 font-medium text-foreground/80 transition-colors hover:bg-white/5 hover:text-foreground'
            route='learningGoalsNew'
          >
            Criar manualmente
          </Anchor>
          <Button
            aria-busy={isPending}
            aria-describedby={isAiQuotaBlocked ? AI_QUOTA_BLOCKED_ID : undefined}
            aria-disabled={isAiQuotaBlocked || undefined}
            disabled={isPending && !isAiQuotaBlocked}
            type='submit'
          >
            {isPending && (
              <Icon className='animate-spin' name='loader-circle' size={16} />
            )}
            {isPending ? 'Planejando...' : 'Planejar com IA'}
          </Button>
        </div>
      </form>
    </section>
  )
}
