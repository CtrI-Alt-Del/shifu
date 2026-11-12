export type AiQuotaWarningDismissalStore = {
  isDismissed(accountId: string, monthKey: string): boolean
  dismiss(accountId: string, monthKey: string): void
}
