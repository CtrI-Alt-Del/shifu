import { Button } from '@/ui/shadcn/button'
import { Checkbox } from '@/ui/shadcn/checkbox'
import { Input } from '@/ui/shadcn/input'
import { Label } from '@/ui/shadcn/label'
import { Textarea } from '@/ui/shadcn/textarea'

import { useGoalCreatePage } from './use-goal-create-page'

export const GoalCreatePage = () => {
  const {
    title,
    description,
    selectedSkillIds,
    skills,
    isLoadingSkills,
    hasSkillsError,
    isSubmitting,
    submissionError,
    setTitle,
    setDescription,
    handleToggleSkill,
    handleRetrySkills,
    handleSubmit,
  } = useGoalCreatePage()

  return (
    <main className='mx-auto w-full max-w-7xl space-y-7 pb-10'>
      <header className='mx-auto w-full max-w-3xl'>
        <p className='text-xs font-bold uppercase tracking-[0.12em] text-primary'>
          Novo Objetivo
        </p>
        <h1 className='mt-2 font-serif text-4xl font-semibold'>
          O que você quer aprender?
        </h1>
        <p className='mt-3 text-muted-foreground'>
          Escolha Habilidades do Currículo. O diagnóstico começa quando você iniciar cada
          Habilidade.
        </p>
      </header>
      <form
        className='mx-auto w-full max-w-3xl space-y-6'
        onSubmit={(event) => void handleSubmit(event)}
      >
        <div className='space-y-2'>
          <Label htmlFor='goal-title'>Título do Objetivo *</Label>
          <Input
            id='goal-title'
            maxLength={120}
            onChange={(event) => setTitle(event.target.value)}
            required
            value={title}
          />
        </div>
        <div className='space-y-2'>
          <Label htmlFor='goal-description'>Descrição *</Label>
          <Textarea
            id='goal-description'
            maxLength={1000}
            onChange={(event) => setDescription(event.target.value)}
            required
            rows={4}
            value={description}
          />
        </div>
        <fieldset className='space-y-3'>
          <legend className='font-serif text-2xl font-semibold'>Habilidades</legend>
          <p className='text-sm text-muted-foreground'>
            Você pode começar com um Objetivo vazio e adicionar Habilidades depois.
          </p>
          {isLoadingSkills ? <output>Carregando Habilidades...</output> : null}
          {hasSkillsError ? (
            <div role='alert'>
              <p>Não foi possível carregar as Habilidades.</p>
              <Button onClick={() => void handleRetrySkills()} type='button'>
                Tentar novamente
              </Button>
            </div>
          ) : null}
          {skills.map((skill) => (
            <div
              className='flex items-start gap-3 rounded-md border border-border bg-card p-4'
              key={skill.id}
            >
              <Checkbox
                checked={selectedSkillIds.includes(skill.id)}
                disabled={!skill.available}
                id={`skill-${skill.id}`}
                label={skill.name}
                onCheckedChange={() => handleToggleSkill(skill.id)}
              />
              {!skill.available ? (
                <p className='mt-1 text-sm text-muted-foreground'>
                  Ainda não disponível para este Objetivo.
                </p>
              ) : null}
            </div>
          ))}
        </fieldset>
        {submissionError ? (
          <p className='text-sm text-destructive' role='alert'>
            {submissionError}
          </p>
        ) : null}
        <Button
          disabled={isSubmitting || !title.trim() || !description.trim()}
          type='submit'
        >
          {isSubmitting ? 'Criando Objetivo...' : 'Criar Objetivo'}
        </Button>
      </form>
    </main>
  )
}
