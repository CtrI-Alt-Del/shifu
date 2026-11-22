import { useState } from 'react'

import type { CatalogSkill } from '@/core/learning/catalog-skill'
import { useAddSkillToGoalAction } from '@/ui/learning/hooks/use-add-skill-to-goal-action'
import { useSkillCatalogQuery } from '@/ui/learning/hooks/use-skill-catalog-query'

const CATALOG_FAILURE_MESSAGE = 'Não foi possível carregar as Habilidades.'

export type UseAddSkillCatalogSectionParams = {
  goalId: string
}

export function useAddSkillCatalogSection({ goalId }: UseAddSkillCatalogSectionParams) {
  const {
    skills,
    skillsError,
    isLoadingSkills,
    isLoadingMoreSkills,
    hasMoreSkills,
    loadMoreSkills,
    retrySkills,
    setSkillCatalogQuery,
  } = useSkillCatalogQuery(goalId)
  const { addSkillToGoal, resetAddSkillToGoal } = useAddSkillToGoalAction(goalId)

  const [selectedSkill, setSelectedSkill] = useState<CatalogSkill | null>(null)
  const [dialogError, setDialogError] = useState<string | null>(null)

  const isLoading = isLoadingSkills || isLoadingMoreSkills
  // A failure that is not an Error must still show as a failure, never as an
  // empty catalog.
  const catalogError =
    skillsError === null || skillsError === undefined
      ? null
      : skillsError instanceof Error
        ? skillsError.message
        : CATALOG_FAILURE_MESSAGE

  function handleSearch(query: string) {
    setSkillCatalogQuery(query)
  }

  function handleSkillSelect(skill: CatalogSkill) {
    setSelectedSkill(skill)
    setDialogError(null)
  }

  function handleDialogClose() {
    setSelectedSkill(null)
    setDialogError(null)
    resetAddSkillToGoal()
  }

  async function handleDialogSubmit(
    selectedFoundationIds: readonly string[],
  ): Promise<void> {
    if (selectedSkill === null) return

    try {
      await addSkillToGoal({
        skillId: selectedSkill.id,
        foundationSkillIds: selectedFoundationIds,
      })
    } catch (error) {
      setDialogError(
        error instanceof Error ? error.message : 'Erro ao adicionar habilidade',
      )
      throw error
    }
  }

  return {
    catalogError,
    dialogError,
    hasMoreSkills,
    isLoading,
    selectedSkill,
    skills,
    handleDialogClose,
    handleDialogSubmit,
    handleSearch,
    handleSkillSelect,
    loadMoreSkills,
    retrySkills,
  }
}
