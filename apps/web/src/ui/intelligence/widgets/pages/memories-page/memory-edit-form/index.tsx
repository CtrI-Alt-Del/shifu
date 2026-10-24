import { useId } from 'react'

import type { LearnerMemory } from '@/core/intelligence/learner-memory'
import { LEARNER_MEMORY_CATEGORY_PRESENTATION } from '@/ui/intelligence/constants/learner-memory-categories'
import { Button } from '@/ui/shadcn/button'
import { Label } from '@/ui/shadcn/label'
import { Textarea } from '@/ui/shadcn/textarea'

import { MEMORY_CONTENT_MAX_LENGTH, useMemoryEditForm } from './use-memory-edit-form'

export type MemoryEditFormProps = {
  memory: LearnerMemory
  isSaving: boolean
  saveError: string | null
  /** Current stored content after a stale save; null when there is no conflict. */
  conflictContent: string | null
  onSave: (content: string) => void
  onCancel: () => void
}

export const MemoryEditForm = ({
  memory,
  isSaving,
  saveError,
  conflictContent,
  onSave,
  onCancel,
}: MemoryEditFormProps) => {
  const contentId = useId()
  const helperId = useId()
  const errorId = useId()
  const {
    content,
    characterCount,
    visibleError,
    handleTextareaRef,
    handleContentChange,
    handleSubmit,
    handleCancel,
  } = useMemoryEditForm({ initialContent: memory.content, onSave, onCancel })

  return (
    <form
      aria-label='Editar memória'
      className='space-y-4 rounded-[10px] border border-border bg-card p-5'
      noValidate
      onSubmit={handleSubmit}
    >
      <h2 className='font-serif text-2xl font-normal'>Editar memória</h2>
      <p className='text-sm text-muted-foreground'>
        {LEARNER_MEMORY_CATEGORY_PRESENTATION[memory.category].label}
      </p>
      <div className='space-y-2'>
        <Label htmlFor={contentId}>Conteúdo</Label>
        <Textarea
          aria-describedby={`${helperId}${visibleError ? ` ${errorId}` : ''}`}
          aria-invalid={visibleError ? true : undefined}
          className='min-h-28'
          disabled={isSaving}
          id={contentId}
          onChange={(event) => handleContentChange(event.currentTarget.value)}
          ref={handleTextareaRef}
          value={content}
        />
        <div className='flex items-start justify-between gap-3 text-xs text-muted-foreground'>
          <p id={helperId}>
            A alteração será usada para adaptar suas explicações. Sua proficiência
            permanece igual.
          </p>
          <p className='shrink-0'>
            <span className='sr-only'>Contagem de caracteres: </span>
            {characterCount}/{MEMORY_CONTENT_MAX_LENGTH}
          </p>
        </div>
        {visibleError ? (
          <p className='text-sm text-selo-text' id={errorId} role='alert'>
            {visibleError}
          </p>
        ) : null}
      </div>
      {conflictContent !== null ? (
        <div
          className='space-y-1 rounded-md border border-control-border p-3 text-sm'
          role='alert'
        >
          <p>
            Esta memória mudou depois que você abriu a edição. Revise seu texto e salve
            novamente.
          </p>
          <p className='break-words text-muted-foreground'>
            Conteúdo atual: {conflictContent}
          </p>
        </div>
      ) : null}
      {saveError ? (
        <p className='text-sm text-selo-text' role='alert'>
          {saveError}
        </p>
      ) : null}
      <div className='flex flex-wrap gap-2'>
        <Button
          className='border border-control-border text-foreground'
          disabled={isSaving}
          onClick={handleCancel}
          type='button'
          variant='ghost'
        >
          Cancelar
        </Button>
        <Button disabled={isSaving} type='submit'>
          {isSaving ? 'Salvando…' : 'Salvar memória'}
        </Button>
      </div>
    </form>
  )
}
