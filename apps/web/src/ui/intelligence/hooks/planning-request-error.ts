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
  'quota-exhausted':
    'Sua cota mensal de IA acabou. O planejamento assistido volta na renovação.',
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

/** True for the refusal that blocks a planning start until the quota renews. */
export function isPlanningQuotaExhaustedError(error: unknown): boolean {
  return error instanceof PlanningRequestError && error.kind === 'quota-exhausted'
}
