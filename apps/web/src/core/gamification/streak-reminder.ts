export type StreakReminderInviteStatus = 'not-eligible' | 'pending' | 'answered'

export type StreakReminder = {
  hour: number
  inviteStatus: StreakReminderInviteStatus
}
