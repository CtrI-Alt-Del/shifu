import { AppError } from './app-error'

export type AuthErrorKind =
  | 'authentication-rejected'
  | 'unavailable'
  | 'invalid-response'
  | 'validation-failed'
  | 'invalid-current-password'
  | 'result-uncertain'

export type AuthErrorOptions = {
  field?: 'displayName' | 'timeZone' | 'newPassword'
  retryAfterSeconds?: number
  statusCode?: number
  cause?: unknown
}

export class AuthError extends AppError {
  readonly kind: AuthErrorKind
  readonly field: AuthErrorOptions['field']
  readonly retryAfterSeconds: number | undefined
  readonly statusCode: number | undefined

  constructor(kind: AuthErrorKind, message: string, options: AuthErrorOptions = {}) {
    super(message, 'Erro de autenticação', { cause: options.cause })
    this.name = 'AuthError'
    this.kind = kind
    this.field = options.field
    this.retryAfterSeconds = options.retryAfterSeconds
    this.statusCode = options.statusCode
  }
}
