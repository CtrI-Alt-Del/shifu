import { AppError } from '@/core/errors/app-error'
import {
  type PlanningFailure,
  type PlanningFailureKind,
  isPlanningFailure,
} from '@/core/intelligence/planning-session'

const DEFAULT_MESSAGES: Record<PlanningFailureKind, string> = {
  unauthorized: 'Sua sessão expirou. Entre novamente para continuar.',
  'not-found': 'Planejamento não encontrado.',
  conflict: 'Já existe uma operação em andamento neste planejamento.',
  'invalid-request': 'As respostas enviadas não são válidas para este conjunto.',
  unavailable: 'Não foi possível falar com o Shifu agora. Tente novamente.',
}

export class PlanningRequestError extends AppError {
  readonly kind: PlanningFailureKind

  constructor(failure: PlanningFailure) {
    super(failure.message || DEFAULT_MESSAGES[failure.kind], 'Planejamento')
    this.name = 'PlanningRequestError'
    this.kind = failure.kind
  }
}

export function unwrapPlanningResult<Result>(result: Result | PlanningFailure): Result {
  if (isPlanningFailure(result)) throw new PlanningRequestError(result)
  return result
}
