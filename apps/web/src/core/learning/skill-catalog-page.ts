import type { CatalogSkill } from './catalog-skill'

export type SkillCatalogPage = {
  items: readonly CatalogSkill[]
  nextCursor: string | null
}
