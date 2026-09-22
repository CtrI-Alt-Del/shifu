import { Button } from '@/ui/shadcn/button'
import { Label } from '@/ui/shadcn/label'
import { Textarea } from '@/ui/shadcn/textarea'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { usePlanningIntentComposer } from './use-planning-intent-composer'

export const PlanningIntentComposer = () => {
  const {
    handleIntentChange,
    handleSubmit,
    intent,
    isPending,
    startPlanningErrorMessage,
    textareaRef,
    validationMessage,
  } = usePlanningIntentComposer()

  return (
    <section className='rounded-3xl border border-border bg-card p-7 sm:p-9'>
      <h1 className='max-w-2xl font-serif text-4xl leading-tight tracking-tight sm:text-5xl'>
        O que você quer aprender?
      </h1>
      <p className='mt-4 max-w-xl leading-7 text-muted-foreground'>
        Descreva com suas palavras. O Shifu monta uma proposta com Habilidades reais e
        você confirma antes de criar.
      </p>

      <form className='mt-7' noValidate onSubmit={handleSubmit}>
        <Label className='sr-only' htmlFor='planning-intent'>
          O que você quer aprender?
        </Label>
        <Textarea
          aria-describedby={validationMessage ? 'planning-intent-validation' : undefined}
          aria-invalid={Boolean(validationMessage)}
          disabled={isPending}
          id='planning-intent'
          onChange={(event) => handleIntentChange(event.target.value)}
          placeholder='Ex.: quero conseguir automatizar tarefas repetitivas com Python'
          ref={textareaRef}
          rows={4}
          value={intent}
        />

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

        <div className='mt-6 flex flex-col-reverse gap-4 sm:flex-row sm:items-center sm:justify-between'>
          <Anchor
            className='inline-flex min-h-11 items-center justify-center rounded-md px-4 font-semibold text-muted-foreground transition-colors hover:bg-white/5 hover:text-foreground'
            route='learningGoalsNew'
          >
            Criar manualmente
          </Anchor>
          <Button aria-busy={isPending} disabled={isPending} type='submit'>
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
