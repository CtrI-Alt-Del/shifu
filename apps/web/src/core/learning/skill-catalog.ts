export type SkillFoundationStatus = 'present' | 'missing'

export type SuggestedFoundation = {
  skillId: string
  name: string
  status: SkillFoundationStatus
}

export type CatalogSkill = {
  id: string
  name: string
  description: string
  alreadyInGoal: boolean
  skillExperienceId: string | null
  foundations: readonly SuggestedFoundation[]
}

export type SkillCatalogPage = {
  items: readonly CatalogSkill[]
  nextCursor: string | null
}

export type CreatedSkillExperience = {
  id: string
  skillId: string
  status: string
}
