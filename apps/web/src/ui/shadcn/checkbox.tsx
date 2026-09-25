import type { InputHTMLAttributes } from 'react'

export type CheckboxProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'checked' | 'onChange' | 'type'
> & {
  checked: boolean
  label: string
  onCheckedChange: (checked: boolean) => void
}

export const Checkbox = ({
  checked,
  className = '',
  label,
  onCheckedChange,
  ...props
}: CheckboxProps) => {
  return (
    <label
      className={`group flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-control-border bg-muted px-4 py-3 text-foreground transition-colors hover:bg-accent has-[:checked]:border-selo-text has-[:checked]:bg-accent ${className}`}
    >
      <input
        aria-label={label}
        checked={checked}
        className='peer sr-only'
        data-focus-ring='delegated'
        onChange={(event) => onCheckedChange(event.currentTarget.checked)}
        type='checkbox'
        {...props}
      />
      <span
        aria-hidden='true'
        className='grid size-5 shrink-0 place-items-center rounded-sm border border-control-border text-transparent peer-checked:border-selo-text peer-checked:text-selo-text peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-selo-text'
      >
        ✓
      </span>
      <span className='min-w-0 flex-1 whitespace-pre-wrap'>{label}</span>
    </label>
  )
}
