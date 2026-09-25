import type { SuggestedFoundation } from './suggested-foundation'

export type CatalogSkill = {
  id: string
  name: string
  description: string
  alreadyInGoal: boolean
  skillExperienceId: string | null
  foundations: readonly SuggestedFoundation[]
}
