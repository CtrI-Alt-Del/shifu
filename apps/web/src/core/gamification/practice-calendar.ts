export type CalendarDayState =
  | 'neutral'
  | 'practiced'
  | 'current-streak'
  | 'missed'
  | 'today-pending'

export type CalendarDay = {
  day: string
  state: CalendarDayState
}

export type PracticeStreak = {
  current: number
  longest: number
}

export type PracticeCalendar = {
  year: number
  month: number
  today: string
  days: CalendarDay[]
  streak: PracticeStreak
  earliestPracticeDate: string | null
}
