import { useState } from 'react'

import type { SkillExperienceReference } from '@/core/learning/skill-experience-reference'
import type { SuggestedFoundation } from '@/core/learning/suggested-foundation'
import { useSkillExperiencesOfSkillQuery } from '@/ui/learning/hooks/use-skill-experiences-of-skill-query'

const NO_FOUNDATIONS_DESCRIPTION =
  'Esta Habilidade não possui bases sugeridas no Currículo.'
const FOUNDATIONS_DESCRIPTION = 'Selecione as bases que deseja adicionar'
const SKILL_ONLY_NOTE = 'A Habilidade será adicionada como não iniciada.'
const SKILL_WITH_FOUNDATIONS_NOTE =
  'A Habilidade e as bases selecionadas serão adicionadas como não iniciadas.'

export type UseAddSkillFoundationsDialogParams = {
  goalId: string
  skillId: string
  foundations: readonly SuggestedFoundation[]
  onClose: () => void
  onSubmit: (selectedFoundationIds: readonly string[]) => Promise<void>
}

export function useAddSkillFoundationsDialog({
  goalId,
  skillId,
  foundations,
  onClose,
  onSubmit,
}: UseAddSkillFoundationsDialogParams) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [isSubmitting, setIsSubmitting] = useState(false)
  // The owner mounts the dialog when a Skill is picked, so the element that has
  // focus on the first render is the Skill action that opened it.
  const [returnFocusElement] = useState(() =>
    typeof document === 'undefined' ? null : document.activeElement,
  )
  // A failed or loading lookup leaves the list empty, so the notice is simply
  // omitted. The addition never waits on this query.
  const { skillExperiencesOfSkill } = useSkillExperiencesOfSkillQuery(skillId)

  const otherGoalExperiences: SkillExperienceReference[] = skillExperiencesOfSkill.filter(
    (experience) => experience.goalId !== goalId,
  )
  const missingFoundations = foundations.filter(
    (foundation) => foundation.status === 'missing',
  )
  const presentFoundations = foundations.filter(
    (foundation) => foundation.status === 'present',
  )
  const hasFoundations = foundations.length > 0
  const description = hasFoundations
    ? FOUNDATIONS_DESCRIPTION
    : NO_FOUNDATIONS_DESCRIPTION
  const note = selectedIds.size > 0 ? SKILL_WITH_FOUNDATIONS_NOTE : SKILL_ONLY_NOTE

  function isFoundationSelected(foundationSkillId: string): boolean {
    return selectedIds.has(foundationSkillId)
  }

  function handleToggle(foundationSkillId: string) {
    setSelectedIds((previous) => {
      const next = new Set(previous)
      if (next.has(foundationSkillId)) {
        next.delete(foundationSkillId)
      } else {
        next.add(foundationSkillId)
      }
      return next
    })
  }

  function handleCloseAutoFocus(event: Event) {
    // Radix would focus a trigger, but this dialog has none.
    event.preventDefault()
    if (returnFocusElement instanceof HTMLElement && returnFocusElement.isConnected) {
      returnFocusElement.focus()
    }
  }

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen && !isSubmitting) onClose()
  }

  async function handleSubmit() {
    if (isSubmitting) return

    setIsSubmitting(true)
    // A rejection is already shown by the owner through the `error` prop, so
    // the dialog only needs to know whether it may close.
    const wasAdded = await onSubmit(Array.from(selectedIds)).then(
      () => true,
      () => false,
    )
    setIsSubmitting(false)
    if (!wasAdded) return

    setSelectedIds(new Set())
    onClose()
  }

  return {
    description,
    hasFoundations,
    isSubmitting,
    missingFoundations,
    note,
    otherGoalExperiences,
    presentFoundations,
    isFoundationSelected,
    handleCloseAutoFocus,
    handleOpenChange,
    handleSubmit,
    handleToggle,
  }
}
