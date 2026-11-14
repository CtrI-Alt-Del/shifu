import type { ReactNode } from 'react'

import { Icon, type IconName } from '@/ui/shared/widgets/components/icon'

export type PlanningOutcomeProps = {
  icon: IconName
  tone: 'neutral' | 'alert'
  title: string
  description: string
  actions: ReactNode
  actionsLayout?: 'row' | 'stack'
}

export const PlanningOutcome = ({
  icon,
  tone,
  title,
  description,
  actions,
  actionsLayout = 'row',
}: PlanningOutcomeProps) => {
  const headingId = 'planning-outcome-title'

  return (
    <section
      aria-labelledby={headingId}
      className='mx-auto flex w-full max-w-[640px] flex-col items-center gap-6 text-center'
    >
      <div
        className={`grid size-14 shrink-0 place-items-center rounded-full ${
          tone === 'alert' ? 'bg-accent' : 'bg-muted'
        }`}
      >
        <Icon
          className={tone === 'alert' ? 'text-selo-text' : 'text-secondary-foreground'}
          name={icon}
          size={24}
        />
      </div>
      <h1
        className='font-serif text-3xl leading-[1.3] text-foreground lg:text-4xl'
        id={headingId}
      >
        {title}
      </h1>
      <p className='text-base leading-6 text-secondary-foreground'>{description}</p>
      <div
        className={
          actionsLayout === 'stack'
            ? 'flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:items-center sm:justify-center sm:gap-3'
            : 'flex flex-row flex-wrap items-center justify-center gap-2.5'
        }
      >
        {actions}
      </div>
    </section>
  )
}
