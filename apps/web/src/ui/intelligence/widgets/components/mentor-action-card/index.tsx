import { Fragment, useId, type ReactNode, type Ref } from 'react'

import { Button } from '@/ui/shadcn/button'
import { Icon, type IconName } from '@/ui/shared/widgets/components/icon'

export type MentorActionCardTone = 'jade' | 'danger' | 'muted'

export type MentorActionCardAction = {
  key: string
  label: string
  variant: 'primary' | 'danger' | 'outline'
  disabled?: boolean
  onSelect?: () => void
  /** Renders a typed router link with the card's button styling instead of a button. */
  renderLink?: (className: string) => ReactNode
}

export type MentorActionCardProps = {
  icon: { name: IconName; tone: MentorActionCardTone }
  title: string
  isTitleVisible?: boolean
  destination?: string
  reason?: string
  consequences?: string
  result?: string
  statusText?: string
  actions: MentorActionCardAction[]
  children?: ReactNode
  resultRef?: Ref<HTMLDivElement>
  titleRef?: Ref<HTMLHeadingElement>
}

const ICON_TONE_CLASS: Record<MentorActionCardTone, string> = {
  jade: 'bg-jade-tint text-jade-text',
  danger: 'bg-danger/15 text-selo-text',
  muted: 'bg-muted text-muted-foreground',
}

const OUTLINE_CLASS = 'border border-control-border! text-foreground!'

const LINK_CLASS: Record<MentorActionCardAction['variant'], string> = {
  primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
  danger: 'bg-danger text-white hover:bg-danger/90',
  outline: `${OUTLINE_CLASS} bg-transparent hover:bg-white/5`,
}

const LINK_BASE_CLASS =
  'inline-flex min-h-11 items-center justify-center rounded-md px-4 font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-selo-text'

export const MentorActionCard = ({
  icon,
  title,
  isTitleVisible = true,
  destination,
  reason,
  consequences,
  result,
  statusText,
  actions,
  children,
  resultRef,
  titleRef,
}: MentorActionCardProps) => {
  const titleId = useId()

  return (
    <section
      aria-labelledby={titleId}
      className='flex w-full min-w-0 max-w-[640px] flex-col gap-3 rounded-[10px] border border-border bg-surface-alt px-[18px] py-4 text-foreground'
    >
      <div className={isTitleVisible ? 'flex items-center gap-3' : 'sr-only'}>
        <span
          className={`flex size-[30px] shrink-0 items-center justify-center rounded-md ${ICON_TONE_CLASS[icon.tone]}`}
        >
          <Icon name={icon.name} size={17} />
        </span>
        <h3
          className='min-w-0 break-words text-base font-semibold text-foreground outline-none'
          id={titleId}
          ref={titleRef}
          tabIndex={-1}
        >
          {title}
        </h3>
      </div>
      {destination ? (
        <p className='break-words text-[13px] leading-normal text-foreground'>
          {destination}
        </p>
      ) : null}
      {children}
      {reason ? (
        <p className='whitespace-pre-line break-words text-sm text-secondary-foreground'>
          {reason}
        </p>
      ) : null}
      {consequences ? (
        <p className='break-words text-[13px] leading-normal text-secondary-foreground'>
          {consequences}
        </p>
      ) : null}
      <div
        aria-live='polite'
        className='flex flex-col gap-3 outline-none empty:sr-only'
        ref={resultRef}
        role='status'
        tabIndex={-1}
      >
        {result ? (
          <p className='break-words text-sm text-secondary-foreground'>{result}</p>
        ) : null}
        {statusText ? (
          <p className='break-words text-[13px] text-muted-foreground'>{statusText}</p>
        ) : null}
      </div>
      {actions.length > 0 ? (
        <div className='flex justify-end gap-2.5 max-[480px]:flex-col max-[480px]:[&>*]:w-full'>
          {actions.map((action) =>
            action.renderLink ? (
              <Fragment key={action.key}>
                {action.renderLink(`${LINK_BASE_CLASS} ${LINK_CLASS[action.variant]}`)}
              </Fragment>
            ) : (
              <Button
                className={action.variant === 'outline' ? OUTLINE_CLASS : ''}
                disabled={action.disabled}
                key={action.key}
                onClick={action.onSelect}
                type='button'
                variant={
                  action.variant === 'danger'
                    ? 'danger'
                    : action.variant === 'outline'
                      ? 'ghost'
                      : 'default'
                }
              >
                {action.label}
              </Button>
            ),
          )}
        </div>
      ) : null}
    </section>
  )
}
