import { type ReactNode, useState } from 'react'

import type { CatalogSkill } from '@/core/learning/catalog-skill'

import { useAddSkillToGoalAction } from '@/ui/learning/hooks/use-add-skill-to-goal-action'
import { useSkillCatalogQuery } from '@/ui/learning/hooks/use-skill-catalog-query'

import { AddSkillFoundationsDialog } from '../../components/add-skill-foundations-dialog'
import { SearchSkillCatalogInput } from '../../components/search-skill-catalog-input'
import { SkillCatalogView } from '../../components/skill-catalog-view'

type AddSkillCatalogSectionProps = {
  goalId: string
}

export function AddSkillCatalogSection({
  goalId,
}: AddSkillCatalogSectionProps): ReactNode {
  const {
    skills,
    skillsError,
    isLoadingSkills,
    isLoadingMoreSkills,
    hasMoreSkills,
    loadMoreSkills,
    setSkillCatalogQuery,
  } = useSkillCatalogQuery(goalId)
  const { addSkillToGoal, resetAddSkillToGoal } = useAddSkillToGoalAction(goalId)

  const [selectedSkill, setSelectedSkill] = useState<CatalogSkill | null>(null)
  const [dialogError, setDialogError] = useState<string | null>(null)

  const handleSkillSelect = (skill: CatalogSkill) => {
    setSelectedSkill(skill)
    setDialogError(null)
  }

  const handleDialogClose = () => {
    setSelectedSkill(null)
    setDialogError(null)
    resetAddSkillToGoal()
  }

  const handleDialogSubmit = async (
    selectedFoundationIds: readonly string[],
  ): Promise<void> => {
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

  return (
    <div className='w-full'>
      <div className='mb-6'>
        <h2 className='mb-4 text-2xl font-semibold'>Adicionar Habilidade</h2>
        <SearchSkillCatalogInput
          onSearch={setSkillCatalogQuery}
          placeholder='Procurar habilidade...'
        />
      </div>

      <SkillCatalogView
        skills={skills}
        isLoading={isLoadingSkills || isLoadingMoreSkills}
        error={skillsError instanceof Error ? skillsError.message : null}
        onSkillSelect={handleSkillSelect}
        onLoadMore={loadMoreSkills}
        hasMore={hasMoreSkills}
      />

      {selectedSkill !== null && (
        <AddSkillFoundationsDialog
          skillName={selectedSkill.name}
          foundations={selectedSkill.foundations}
          isOpen
          error={dialogError}
          onClose={handleDialogClose}
          onSubmit={handleDialogSubmit}
        />
      )}
    </div>
  )
}
