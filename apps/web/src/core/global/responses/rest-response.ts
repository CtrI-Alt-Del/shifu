import { HTTP_STATUS_CODE } from '../constants/http-status-code'

type RestResponseProps<Body> = {
  body?: Body
  statusCode?: number
  errorMessage?: string
  headers?: Record<string, string>
}

export class RestResponse<Body = unknown> {
  private readonly _body: Body | null
  private readonly _errorMessage: string | null
  readonly statusCode: number = HTTP_STATUS_CODE.ok
  readonly headers: Record<string, string> = {}

  constructor({ body, statusCode, errorMessage, headers }: RestResponseProps<Body> = {}) {
    this._body = body ?? null
    this._errorMessage = errorMessage ?? null
    if (statusCode) this.statusCode = statusCode
    if (headers) this.headers = headers
  }

  get isSuccessful() {
    return this.statusCode <= HTTP_STATUS_CODE.redirect
  }

  get isFailure() {
    return this.statusCode >= HTTP_STATUS_CODE.badRequest || Boolean(this._errorMessage)
  }

  get body(): Body {
    if (this._errorMessage) {
      throw new Error(this._errorMessage)
    }
    return this._body as Body
  }

  get errorMessage(): string {
    if (!this._errorMessage) {
      throw new Error('Rest Response has no error message')
    }
    return this._errorMessage
  }
}
