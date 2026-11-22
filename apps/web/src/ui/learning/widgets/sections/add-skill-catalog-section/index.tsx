import type { ReactNode } from 'react'

import { AddSkillFoundationsDialog } from '../../components/add-skill-foundations-dialog'
import { SearchSkillCatalogInput } from '../../components/search-skill-catalog-input'
import { SkillCatalogView } from '../../components/skill-catalog-view'
import { useAddSkillCatalogSection } from './use-add-skill-catalog-section'

export type AddSkillCatalogSectionProps = {
  goalId: string
}

export const AddSkillCatalogSection = ({
  goalId,
}: AddSkillCatalogSectionProps): ReactNode => {
  const {
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
  } = useAddSkillCatalogSection({ goalId })

  return (
    <div className='flex w-full flex-col gap-4 sm:gap-6'>
      <SearchSkillCatalogInput onSearch={handleSearch} />

      <SkillCatalogView
        error={catalogError}
        hasMore={hasMoreSkills}
        isLoading={isLoading}
        onLoadMore={loadMoreSkills}
        onRetry={retrySkills}
        onSkillSelect={handleSkillSelect}
        skills={skills}
      />

      {selectedSkill !== null ? (
        <AddSkillFoundationsDialog
          error={dialogError}
          foundations={selectedSkill.foundations}
          goalId={goalId}
          isOpen
          onClose={handleDialogClose}
          onSubmit={handleDialogSubmit}
          skillId={selectedSkill.id}
          skillName={selectedSkill.name}
        />
      ) : null}
    </div>
  )
}
