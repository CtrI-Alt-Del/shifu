import { AuthError } from '@/core/errors/auth-error'
import {
  parseCompetencyDetail,
  type CompetencyDetail,
} from '@/core/learning/competency-detail'
import { RestError } from '@/core/errors/rest-error'
import {
  getCompetencyDetailAction,
  type GetCompetencyDetailActionResult,
} from '@/rpc/actions/learning/get-competency-detail-action'
import type {
  AvailableCompetencyDetailResponse,
  CompetencyActivityDetailResponse,
  CompetencyDetailResponse,
  CompetencyDetailResponseItem,
  CompetencyMaterialDetailResponse,
  UnavailableCompetencyDetailResponse,
} from '@/rest/services/learning-service'

export type LearningRpcService = ReturnType<typeof LearningRpcService>

export const LearningRpcService = () => {
  return {
    async getCompetencyDetail(
      goalId: string,
      skillId: string,
      competencyId: string,
    ): Promise<CompetencyDetail> {
      const result = await getCompetencyDetailAction({
        data: { goalId, skillId, competencyId },
      })

      if (isFailure(result)) mapFailure(result)

      const detail = parseCompetencyDetail(mapResponse(result))
      if (!detail) {
        throw new RestError('A resposta de aprendizagem é inválida.', 503)
      }

      return detail
    },
  }
}

function mapResponse(response: CompetencyDetailResponse): unknown {
  if (response.availability === 'unavailable') {
    return mapUnavailableResponse(response)
  }

  return mapAvailableResponse(response)
}

function mapAvailableResponse(response: AvailableCompetencyDetailResponse) {
  return {
    availability: 'available' as const,
    goalId: response.goal_id,
    skillId: response.skill_id,
    skillName: response.skill_name,
    competencyId: response.competency_id,
    competencyName: response.competency_name,
    progress: response.progress,
    status: response.status,
    isFocus: response.is_focus,
    focusReturned: response.focus_returned,
    focusCompetencyId: response.focus_competency_id,
    focusCompetencyName: response.focus_competency_name,
    items: response.items.map(mapResponseItem),
    recommendation: response.recommendation
      ? {
          competencyId: response.recommendation.competency_id,
          activityId: response.recommendation.activity_id,
          difficulty: response.recommendation.difficulty,
          type: response.recommendation.type,
        }
      : null,
  }
}

function mapUnavailableResponse(response: UnavailableCompetencyDetailResponse) {
  return {
    availability: 'unavailable' as const,
    goalId: response.goal_id,
    skillId: response.skill_id,
    skillName: response.skill_name,
    competencyId: response.competency_id,
    competencyName: response.competency_name,
    focusCompetencyId: response.focus_competency_id,
    focusCompetencyName: response.focus_competency_name,
  }
}

function mapResponseItem(
  item: CompetencyDetailResponseItem,
): CompetencyMaterialDetailResponse | CompetencyActivityDetailResponse | unknown {
  if (item.kind === 'material') {
    return {
      kind: 'material' as const,
      id: item.id,
      title: item.title,
      position: item.position,
    }
  }

  return {
    kind: 'activity' as const,
    id: item.id,
    title: item.title,
    position: item.position,
    activityType: item.activity_type,
    difficulty: item.difficulty,
    latestScore: item.latest_score,
  }
}

function isFailure(
  result: GetCompetencyDetailActionResult,
): result is Exclude<GetCompetencyDetailActionResult, CompetencyDetailResponse> {
  return 'kind' in result
}

function mapFailure(
  failure: Exclude<GetCompetencyDetailActionResult, CompetencyDetailResponse>,
): never {
  if (failure.kind === 'unauthorized') {
    throw new AuthError('authentication-rejected', 'Sua sessão expirou.', {
      statusCode: 401,
    })
  }

  if (failure.kind === 'not-found') {
    throw new RestError('Recurso não encontrado.', 404)
  }

  if (failure.kind === 'invalid-request') {
    throw new RestError('A solicitação de aprendizagem é inválida.', 422)
  }

  throw new RestError('Serviço temporariamente indisponível.', failure.statusCode ?? 503)
}
