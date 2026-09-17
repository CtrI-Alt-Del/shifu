export class AppError extends Error {
  readonly title: string

  constructor(message: string, title = 'Erro', options?: ErrorOptions) {
    super(message, options)
    this.name = 'AppError'
    this.title = title
  }
}
