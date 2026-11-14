import type { AchievementFamily } from '@/core/gamification/achievement'
import type { IconName } from '@/ui/shared/widgets/components/icon'

export const ACHIEVEMENT_FAMILY_LABELS: Record<AchievementFamily, string> = {
  diagnosis: 'Diagnóstico',
  mastery: 'Domínio',
  completion: 'Conclusão',
  streak: 'Sequência',
  level: 'Nível',
}

// A code missing here (a retired or newly added catalog entry) falls back to
// its family's symbol, so every medal still carries a glyph.
export const ACHIEVEMENT_FAMILY_ICONS: Record<AchievementFamily, IconName> = {
  diagnosis: 'compass',
  mastery: 'target',
  completion: 'flag',
  streak: 'flame',
  level: 'award',
}

export const ACHIEVEMENT_CODE_ICONS: Record<string, IconName> = {
  'primeiro-passo': 'footprints',
  explorador: 'compass',
  'primeiro-dominio': 'target',
  'em-evolucao': 'trending-up',
  'primeira-jornada': 'flag',
  'colecionador-de-habilidades': 'layers',
  'consistencia-i': 'flame',
  'consistencia-ii': 'flame',
  'consistencia-iii': 'flame',
  'ascendente-i': 'award',
  'ascendente-ii': 'award',
  'ascendente-iii': 'award',
}
