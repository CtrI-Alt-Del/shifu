import { Button } from '@/ui/shadcn/button'
import { Icon } from '@/ui/shared/widgets/components/icon'

import { CalendarLegend } from './calendar-legend'
import { MonthNavigator } from './month-navigator'
import { PracticeCalendarGrid } from './practice-calendar-grid'
import { SelectedDayConfirmation } from './selected-day-confirmation'
import { StreakPanel } from './streak-panel'
import { useCalendarTabPanel } from './use-calendar-tab-panel'

export const CalendarTabPanel = () => {
  const {
    viewedMonth,
    calendar,
    selectedDay,
    state,
    isAtCurrentMonth,
    isAtEarliestMonth,
    isRetrying,
    goToPreviousMonth,
    goToNextMonth,
    handleSelectDay,
    handleRetry,
  } = useCalendarTabPanel()

  if (state === 'loading') {
    return (
      <output
        aria-busy='true'
        aria-label='Carregando calendário de prática'
        className='block space-y-5 rounded-lg border border-border bg-card p-6'
      >
        <div aria-hidden='true' className='h-16 w-full animate-pulse rounded bg-muted' />
        <div aria-hidden='true' className='h-80 animate-pulse rounded bg-muted' />
        <span className='sr-only'>Carregando calendário de prática</span>
      </output>
    )
  }

  if (state === 'error' || !calendar) {
    return (
      <section
        aria-labelledby='gamification-calendar-error-title'
        className='rounded-lg border border-border bg-card p-8 text-center'
        role='alert'
      >
        <Icon className='mx-auto text-selo-text' name='circle-alert' size={32} />
        <h3
          autoFocus
          className='mt-4 font-serif text-2xl'
          id='gamification-calendar-error-title'
          tabIndex={-1}
        >
          Não foi possível carregar seu calendário
        </h3>
        <p className='mt-3 text-muted-foreground'>
          Seus dias de prática continuam salvos. Tente novamente em alguns instantes.
        </p>
        <Button
          className='mt-6'
          disabled={isRetrying}
          onClick={handleRetry}
          type='button'
        >
          Tentar novamente
        </Button>
      </section>
    )
  }

  const isTodayPending = calendar.days.some(
    (day) => day.day === calendar.today && day.state === 'today-pending',
  )

  return (
    <div className='space-y-8'>
      <div className='flex flex-col gap-8 lg:flex-row'>
        <section
          aria-label='Calendário de prática'
          className='flex-1 space-y-6 rounded-[10px] bg-card p-6'
        >
          <MonthNavigator
            isAtCurrentMonth={isAtCurrentMonth}
            isAtEarliestMonth={isAtEarliestMonth}
            month={viewedMonth.month}
            onNextMonth={goToNextMonth}
            onPreviousMonth={goToPreviousMonth}
            year={viewedMonth.year}
          />
          <PracticeCalendarGrid
            days={calendar.days}
            onSelectDay={handleSelectDay}
            selectedDay={selectedDay}
          />
          <SelectedDayConfirmation selectedDay={selectedDay} />
        </section>
        <div className='lg:w-[360px]'>
          <StreakPanel
            isTodayPending={isTodayPending}
            streak={calendar.streak}
            today={calendar.today}
          />
        </div>
      </div>
      <CalendarLegend />
    </div>
  )
}
