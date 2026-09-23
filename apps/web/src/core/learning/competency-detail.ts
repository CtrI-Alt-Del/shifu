export const COMPETENCY_DETAIL_ID_PATTERN = /^[A-Z0-9]{26}$/

export type CompetencyAvailability = 'available' | 'unavailable'
export type CompetencyProgressStatus =
  | 'learning'
  | 'developing'
  | 'proficient'
  | 'mastered'
export type ActivityDifficulty = 'easy' | 'medium' | 'hard'
export type ActivityRecommendationType = 'new-activity' | 'reinforcement'

export type CompetencyMaterialDetail = {
  kind: 'material'
  id: string
  title: string
  position: number
}

export type CompetencyActivityDetail = {
  kind: 'activity'
  id: string
  title: string
  position: number
  activityType: string
  difficulty: ActivityDifficulty
  latestScore: number | null
}

export type CompetencyDetailItem = CompetencyMaterialDetail | CompetencyActivityDetail

export type ActivityRecommendation = {
  competencyId: string
  activityId: string
  difficulty: ActivityDifficulty
  type: ActivityRecommendationType
}

export type AvailableCompetencyDetail = {
  availability: 'available'
  goalId: string
  skillId: string
  skillName: string
  competencyId: string
  competencyName: string
  progress: number
  status: CompetencyProgressStatus
  isFocus: boolean
  focusReturned: boolean
  focusCompetencyId: string | null
  focusCompetencyName: string | null
  items: readonly CompetencyDetailItem[]
  recommendation: ActivityRecommendation | null
}

export type UnavailableCompetencyDetail = {
  availability: 'unavailable'
  goalId: string
  skillId: string
  skillName: string
  competencyId: string
  competencyName: string
  focusCompetencyId: string | null
  focusCompetencyName: string | null
}

export type CompetencyDetail = AvailableCompetencyDetail | UnavailableCompetencyDetail

export function parseCompetencyDetail(value: unknown): CompetencyDetail | null {
  return isCompetencyDetail(value) ? value : null
}

export function isCompetencyDetail(value: unknown): value is CompetencyDetail {
  if (!isRecord(value) || !isIdentifier(value.goalId) || !isIdentifier(value.skillId)) {
    return false
  }

  if (
    !isIdentifier(value.competencyId) ||
    !isNonEmptyString(value.skillName) ||
    !isNonEmptyString(value.competencyName)
  ) {
    return false
  }

  if (value.availability === 'unavailable') {
    return (
      isNullableIdentifier(value.focusCompetencyId) &&
      isNullableString(value.focusCompetencyName)
    )
  }

  return (
    value.availability === 'available' &&
    isPercentage(value.progress) &&
    isCompetencyProgressStatus(value.status) &&
    typeof value.isFocus === 'boolean' &&
    typeof value.focusReturned === 'boolean' &&
    isNullableIdentifier(value.focusCompetencyId) &&
    isNullableString(value.focusCompetencyName) &&
    Array.isArray(value.items) &&
    value.items.every(isCompetencyDetailItem) &&
    (value.recommendation === null || isActivityRecommendation(value.recommendation))
  )
}

function isCompetencyDetailItem(value: unknown): value is CompetencyDetailItem {
  if (!isRecord(value) || !isIdentifier(value.id) || !isNonEmptyString(value.title)) {
    return false
  }

  if (value.kind === 'material') {
    return isPosition(value.position)
  }

  return (
    value.kind === 'activity' &&
    isPosition(value.position) &&
    isNonEmptyString(value.activityType) &&
    isActivityDifficulty(value.difficulty) &&
    (value.latestScore === null || isPercentage(value.latestScore))
  )
}

function isActivityRecommendation(value: unknown): value is ActivityRecommendation {
  return (
    isRecord(value) &&
    isIdentifier(value.competencyId) &&
    isIdentifier(value.activityId) &&
    isActivityDifficulty(value.difficulty) &&
    isActivityRecommendationType(value.type)
  )
}

function isActivityDifficulty(value: unknown): value is ActivityDifficulty {
  return value === 'easy' || value === 'medium' || value === 'hard'
}

function isActivityRecommendationType(
  value: unknown,
): value is ActivityRecommendationType {
  return value === 'new-activity' || value === 'reinforcement'
}

function isCompetencyProgressStatus(value: unknown): value is CompetencyProgressStatus {
  return (
    value === 'learning' ||
    value === 'developing' ||
    value === 'proficient' ||
    value === 'mastered'
  )
}

function isIdentifier(value: unknown): value is string {
  return typeof value === 'string' && COMPETENCY_DETAIL_ID_PATTERN.test(value)
}

function isNullableIdentifier(value: unknown): value is string | null {
  return value === null || isIdentifier(value)
}

function isNullableString(value: unknown): value is string | null {
  return value === null || isNonEmptyString(value)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.length > 0
}

function isPercentage(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 100
}

function isPosition(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
