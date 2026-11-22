export type SkillEvolutionPoint = {
  /** UTC instant, ISO 8601. */
  occurredAt: string
  /** Habilidade result, 0..100. */
  result: number
  isPartial: boolean
  isBaseline: boolean
}

export type SkillEvolution = {
  skillExperienceId: string
  /** Chronological. */
  points: SkillEvolutionPoint[]
}
