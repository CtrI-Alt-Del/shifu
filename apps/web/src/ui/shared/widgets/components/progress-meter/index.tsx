export type ProgressMeterProps = {
  label?: string
  tone?: 'primary' | 'success'
  value: number
}

export const ProgressMeter = ({ label, tone = 'primary', value }: ProgressMeterProps) => {
  const boundedValue = Math.min(100, Math.max(0, value))
  const toneClassName = tone === 'success' ? 'text-success' : 'text-primary'
  const fillClassName = tone === 'success' ? 'bg-success' : 'bg-primary'

  return (
    <div>
      {label ? (
        <div className='mb-2 flex items-center justify-between gap-4 text-sm'>
          <span className='font-semibold text-foreground'>{label}</span>
          <span className={`font-bold ${toneClassName}`}>{boundedValue}%</span>
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
          className={`h-full rounded-full transition-[width] ${fillClassName}`}
          style={{ width: `${boundedValue}%` }}
        />
      </div>
    </div>
  )
}
