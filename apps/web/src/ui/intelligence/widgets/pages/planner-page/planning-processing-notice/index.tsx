import { Icon } from '@/ui/shared/widgets/components/icon'

export type PlanningProcessingNoticeProps = {
  tone: 'processing' | 'failure'
  title: string
  support: string
}

export const PlanningProcessingNotice = ({
  tone,
  title,
  support,
}: PlanningProcessingNoticeProps) => {
  return (
    <div
      aria-live='polite'
      className='flex items-center gap-3 rounded-[10px] border border-border bg-surface-alt p-4'
      role={tone === 'failure' ? 'alert' : 'status'}
    >
      {tone === 'processing' ? (
        <Icon
          className='shrink-0 text-jade-text motion-safe:animate-spin'
          name='loader-circle'
          size={20}
        />
      ) : (
        <Icon className='shrink-0 text-selo-text' name='triangle-alert' size={20} />
      )}
      <div className='flex min-w-0 flex-col gap-1'>
        <p className='text-[15px] font-semibold leading-[1.45] text-foreground'>
          {title}
        </p>
        <p className='text-[13px] leading-[1.45] text-secondary-foreground'>{support}</p>
      </div>
    </div>
  )
}
