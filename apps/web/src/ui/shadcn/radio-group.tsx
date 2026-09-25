import {
  createContext,
  useContext,
  type HTMLAttributes,
  type InputHTMLAttributes,
} from 'react'

type RadioGroupContextValue = {
  name: string
  value: string
  onValueChange: (value: string) => void
  disabled: boolean
}

const RadioGroupContext = createContext<RadioGroupContextValue | null>(null)

export type RadioGroupProps = Omit<HTMLAttributes<HTMLDivElement>, 'onChange'> & {
  name: string
  value: string
  onValueChange: (value: string) => void
  disabled?: boolean
}

export const RadioGroup = ({
  children,
  className = '',
  name,
  onValueChange,
  value,
  disabled = false,
  ...props
}: RadioGroupProps) => {
  return (
    <RadioGroupContext.Provider value={{ disabled, name, onValueChange, value }}>
      <div className={className} role='radiogroup' {...props}>
        {children}
      </div>
    </RadioGroupContext.Provider>
  )
}

export type RadioGroupItemProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  'checked' | 'name' | 'onChange' | 'type'
> & {
  label: string
  value: string
}

export const RadioGroupItem = ({
  className = '',
  label,
  value,
  ...props
}: RadioGroupItemProps) => {
  const group = useContext(RadioGroupContext)

  if (!group) {
    return null
  }

  return (
    <label
      className={`group flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-control-border bg-muted px-4 py-3 text-foreground transition-colors hover:bg-accent has-[:checked]:border-selo-text has-[:checked]:bg-accent ${className}`}
    >
      <input
        aria-label={label}
        checked={group.value === value}
        className='peer sr-only'
        data-focus-ring='delegated'
        disabled={group.disabled || props.disabled}
        name={group.name}
        onChange={() => group.onValueChange(value)}
        type='radio'
        value={value}
        {...props}
      />
      <span
        aria-hidden='true'
        className='grid size-5 shrink-0 place-items-center rounded-full border border-control-border peer-checked:border-selo-text peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-selo-text after:size-2.5 after:rounded-full after:content-[""] peer-checked:after:bg-selo-text'
      />
      <span className='min-w-0 flex-1 whitespace-pre-wrap'>{label}</span>
    </label>
  )
}
