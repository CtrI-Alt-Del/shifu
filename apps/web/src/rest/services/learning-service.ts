import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'
import type { RestClient } from '@/core/shared/interfaces/rest-client'
import {
  COMPETENCY_DETAIL_ID_PATTERN,
  type ActivityDifficulty,
  type ActivityRecommendationType,
  type CompetencyProgressStatus,
} from '@/core/learning/competency-detail'

export type LearningGoalItem = {
  description: string
  id: string
  skill_count: number
  title: string
  updated_at: string
}

export type CompetencyMaterialDetailResponse = {
  kind: 'material'
  id: string
  title: string
  position: number
}

export type CompetencyActivityDetailResponse = {
  kind: 'activity'
  id: string
  title: string
  position: number
  activity_type: string
  difficulty: ActivityDifficulty
  latest_score: number | null
}

export type CompetencyDetailResponseItem =
  | CompetencyMaterialDetailResponse
  | CompetencyActivityDetailResponse

export type ActivityRecommendationResponse = {
  competency_id: string
  activity_id: string
  difficulty: ActivityDifficulty
  type: ActivityRecommendationType
}

export type AvailableCompetencyDetailResponse = {
  availability: 'available'
  goal_id: string
  skill_id: string
  skill_name: string
  competency_id: string
  competency_name: string
  progress: number
  status: CompetencyProgressStatus
  is_focus: boolean
  focus_returned: boolean
  focus_competency_id: string | null
  focus_competency_name: string | null
  items: CompetencyDetailResponseItem[]
  recommendation: ActivityRecommendationResponse | null
}

export type UnavailableCompetencyDetailResponse = {
  availability: 'unavailable'
  goal_id: string
  skill_id: string
  skill_name: string
  competency_id: string
  competency_name: string
  focus_competency_id: string | null
  focus_competency_name: string | null
}

export type CompetencyDetailResponse =
  | AvailableCompetencyDetailResponse
  | UnavailableCompetencyDetailResponse

export type LearningService = ReturnType<typeof LearningService>

export const LearningService = (restClient: RestClient) => {
  return {
    async getGoals(accessToken: string): Promise<LearningGoalItem[]> {
      const response = await restClient.get<{ goals: LearningGoalItem[] }>(
        '/learning/goals',
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) response.throwError()
      return validateGoalsResponse(response.body)
    },

    async getCompetencyDetail(
      accessToken: string,
      goalId: string,
      skillId: string,
      competencyId: string,
    ): Promise<CompetencyDetailResponse> {
      const response = await restClient.get<unknown>(
        `/learning/goals/${goalId}/skills/${skillId}/competencies/${competencyId}`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )

      if (response.isFailure) mapFailure(response.statusCode)

      if (!isCompetencyDetailResponse(response.body)) {
        throw new RestError('A resposta de aprendizagem é inválida.', 503)
      }

      return response.body
    },
  }
}

function validateGoalsResponse(body: unknown): LearningGoalItem[] {
  if (!isRecord(body) || !Array.isArray(body.goals)) {
    throw new AppError('A resposta de Objetivos é inválida.', 'Erro de comunicação')
  }

  return body.goals as LearningGoalItem[]
}

function mapFailure(statusCode: number): never {
  if (statusCode === 401) {
    throw new RestError('A sessão não é mais válida.', 401)
  }

  if (statusCode === 404) {
    throw new RestError('Recurso não encontrado.', 404)
  }

  if (statusCode === 0 || statusCode >= 500) {
    throw new RestError('Serviço temporariamente indisponível.', 503)
  }

  throw new RestError('A resposta de aprendizagem é inválida.', statusCode)
}

function isCompetencyDetailResponse(value: unknown): value is CompetencyDetailResponse {
  if (!isRecord(value) || !isIdentifier(value.goal_id) || !isIdentifier(value.skill_id)) {
    return false
  }

  if (
    !isIdentifier(value.competency_id) ||
    !isNonEmptyString(value.skill_name) ||
    !isNonEmptyString(value.competency_name)
  ) {
    return false
  }

  if (value.availability === 'unavailable') {
    return (
      isNullableIdentifier(value.focus_competency_id) &&
      isNullableString(value.focus_competency_name)
    )
  }

  return (
    value.availability === 'available' &&
    isPercentage(value.progress) &&
    isCompetencyProgressStatus(value.status) &&
    typeof value.is_focus === 'boolean' &&
    typeof value.focus_returned === 'boolean' &&
    isNullableIdentifier(value.focus_competency_id) &&
    isNullableString(value.focus_competency_name) &&
    Array.isArray(value.items) &&
    value.items.every(isCompetencyDetailResponseItem) &&
    (value.recommendation === null ||
      isActivityRecommendationResponse(value.recommendation))
  )
}

function isCompetencyDetailResponseItem(
  value: unknown,
): value is CompetencyDetailResponseItem {
  if (!isRecord(value) || !isIdentifier(value.id) || !isNonEmptyString(value.title)) {
    return false
  }

  if (value.kind === 'material') return isPosition(value.position)

  return (
    value.kind === 'activity' &&
    isPosition(value.position) &&
    isNonEmptyString(value.activity_type) &&
    isActivityDifficulty(value.difficulty) &&
    (value.latest_score === null || isPercentage(value.latest_score))
  )
}

function isActivityRecommendationResponse(
  value: unknown,
): value is ActivityRecommendationResponse {
  return (
    isRecord(value) &&
    isIdentifier(value.competency_id) &&
    isIdentifier(value.activity_id) &&
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
