import type { AiQuotaStatus } from '@/core/intelligence/ai-quota-usage'
import type { IconName } from '@/ui/shared/widgets/components/icon'

/** Every quota state carries an icon next to its text, so color never carries it alone. */
export const AI_QUOTA_STATUS_ICONS: Record<AiQuotaStatus, IconName> = {
  normal: 'sparkles',
  near_limit: 'triangle-alert',
  blocked: 'circle-pause',
}

export const AI_QUOTA_UNAVAILABLE_ICON: IconName = 'circle-dashed'

export const AI_QUOTA_BLOCKED_FALLBACK_MESSAGE =
  'Sua cota mensal de IA acabou. O Mentor e o planejamento assistido voltam na renovação. Seus estudos continuam normalmente.'

/** Surfaces that show the blocked-quota message; each one names what comes back on renewal. */
export type AiQuotaSurface = 'mentor' | 'home' | 'planner-failure' | 'planner-proposal'

const MONTH_NAMES = [
  'janeiro',
  'fevereiro',
  'março',
  'abril',
  'maio',
  'junho',
  'julho',
  'agosto',
  'setembro',
  'outubro',
  'novembro',
  'dezembro',
] as const

const ISO_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})/

const NEXT_RENEWAL_LABEL = 'na próxima renovação'

/** Formats an ISO date as "1º de dezembro de 2026"; day 1 uses the ordinal. */
export function formatAiQuotaRenewalDate(renewsOn: string): string {
  const match = ISO_DATE_PATTERN.exec(renewsOn)
  if (!match) return NEXT_RENEWAL_LABEL

  const year = Number(match[1])
  const monthName = MONTH_NAMES[Number(match[2]) - 1]
  const day = Number(match[3])
  if (!monthName || day < 1 || day > 31) return NEXT_RENEWAL_LABEL

  const dayLabel = day === 1 ? '1º' : String(day)
  return `${dayLabel} de ${monthName} de ${year}`
}

function renewalLabel(renewsOn: string | null): string {
  return renewsOn ? `em ${formatAiQuotaRenewalDate(renewsOn)}` : NEXT_RENEWAL_LABEL
}

export function aiQuotaBlockedMessage(
  surface: AiQuotaSurface,
  renewsOn: string | null,
): string {
  const renewal = renewalLabel(renewsOn)

  switch (surface) {
    case 'mentor':
      return `Sua cota de IA acabou. Novas mensagens e novas tentativas voltam ${renewal}. Seu histórico continua disponível.`
    case 'home':
      return `Sua cota de IA acabou. O planejamento com IA volta ${renewal}. Você pode criar um Objetivo manualmente agora.`
    case 'planner-failure':
      return `Sua cota de IA acabou. Novas tentativas voltam ${renewal}. Você ainda pode cancelar e criar um Objetivo manualmente.`
    case 'planner-proposal':
      return `Sua cota de IA acabou. Reiniciar o planejamento volta ${renewal}. Você ainda pode criar este Objetivo agora.`
  }
}

export function aiQuotaWarningMessage(percentage: number, renewsOn: string): string {
  return `Você já usou ${percentage}% da sua cota de IA deste mês. Quando ela acabar, o Mentor e o planejamento assistido pausam até ${formatAiQuotaRenewalDate(renewsOn)}.`
}
