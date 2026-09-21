import { AppError } from './app-error'

export class RestError extends AppError {
  constructor(
    message: string,
    readonly statusCode: number,
  ) {
    super(message, 'Erro de comunicação')
    this.name = 'RestError'
  }
}
