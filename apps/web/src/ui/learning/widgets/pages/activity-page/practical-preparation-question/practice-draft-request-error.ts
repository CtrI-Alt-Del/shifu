import { AppError } from '@/core/errors/app-error'

import type { PracticeDraftFailure } from './practice-draft-server-functions'

export type PracticeDraftErrorKind =
  | PracticeDraftFailure['kind']
  | 'too-large'
  | 'unsupported'
  | 'upload-key-conflict'

export class PracticeDraftRequestError extends AppError {
  constructor(readonly kind: PracticeDraftErrorKind) {
    super('Não foi possível concluir a operação do rascunho.', 'Erro de comunicação')
    this.name = 'PracticeDraftRequestError'
  }
}
