import { AppError } from '@/core/errors/app-error'
import { RestError } from '@/core/errors/rest-error'

export class RestResponse<ResponseBody> {
  readonly _body: ResponseBody | undefined
  readonly statusCode: number
  readonly headers: Record<string, string>
  readonly errorMessage: string | undefined

  constructor({
    body,
    statusCode,
    headers = {},
    errorMessage,
  }: {
    body?: ResponseBody
    statusCode: number
    headers?: Record<string, string>
    errorMessage?: string
  }) {
    this._body = body
    this.statusCode = statusCode
    this.headers = headers
    this.errorMessage = errorMessage
  }

  get isSuccessful() {
    return this.statusCode >= 200 && this.statusCode < 300
  }

  get isFailure() {
    return !this.isSuccessful
  }

  get body() {
    if (this._body === undefined) {
      throw new AppError(
        'O corpo da resposta REST não foi informado.',
        'Erro de comunicação',
      )
    }
    return this._body
  }

  throwError(): never {
    throw new RestError(
      this.errorMessage ?? 'Não foi possível concluir a solicitação.',
      this.statusCode,
    )
  }
}
