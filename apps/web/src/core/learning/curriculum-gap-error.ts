import { AppError } from '@/core/errors/app-error'

export class CurriculumGapError extends AppError {
  constructor() {
    super(
      'O Currículo desta Habilidade ainda não tem cobertura suficiente para iniciar o diagnóstico.',
      'Cobertura do Currículo insuficiente',
    )
    this.name = 'CurriculumGapError'
  }
}
