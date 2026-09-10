export type ProgressMeterProps = {
  label?: string
  value: number
}

export const ProgressMeter = ({ label, value }: ProgressMeterProps) => {
  const boundedValue = Math.min(100, Math.max(0, value))

  return (
    <div>
      {label ? (
        <div className='mb-2 flex items-center justify-between gap-4 text-sm'>
          <span className='font-semibold text-foreground'>{label}</span>
          <span className='font-bold text-primary'>{boundedValue}%</span>
        </div>
      ) : null}
      <div
        aria-label={label}
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={boundedValue}
        className='h-2.5 overflow-hidden rounded-full bg-muted'
        role='progressbar'
      >
        <div
          className='h-full rounded-full bg-primary transition-[width]'
          style={{ width: `${boundedValue}%` }}
        />
      </div>
    </div>
  )
}
