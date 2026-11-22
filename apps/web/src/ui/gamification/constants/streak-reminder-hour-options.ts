export const STREAK_REMINDER_HOUR_MIN = 6
export const STREAK_REMINDER_HOUR_MAX = 22
export const DEFAULT_STREAK_REMINDER_HOUR = 18

export const STREAK_REMINDER_HOUR_OPTIONS = Array.from(
  { length: STREAK_REMINDER_HOUR_MAX - STREAK_REMINDER_HOUR_MIN + 1 },
  (_, index) => {
    const hour = STREAK_REMINDER_HOUR_MIN + index
    return { value: String(hour), label: `${String(hour).padStart(2, '0')}:00` }
  },
)
