import type { ActivityRecommendation } from '@/core/learning/competency-detail'

export const MATERIAL_DETAIL_ID_PATTERN = /^[A-Z0-9]{26}$/

export type AvailableMaterialDetail = {
  availability: 'available'
  goalId: string
  skillId: string
  skillName: string
  competencyId: string
  competencyName: string
  materialId: string
  materialTitle: string
  content: string
  recommendation: ActivityRecommendation | null
}

export type UnavailableMaterialDetail = {
  availability: 'unavailable'
  goalId: string
  skillId: string
  skillName: string
  competencyId: string
  competencyName: string
  materialId: string
  focusCompetencyId: string | null
  focusCompetencyName: string | null
}

export type MaterialDetail = AvailableMaterialDetail | UnavailableMaterialDetail
