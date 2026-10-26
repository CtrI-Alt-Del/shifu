import { Select as SelectPrimitive } from '@base-ui/react/select'

export type SelectProps = {
  id?: string
  name?: string
  className?: string
  placeholder?: string
  value: string | null
  options: readonly { value: string; label: string }[]
  onValueChange: (value: string | null) => void
  disabled?: boolean
  required?: boolean
  'aria-label'?: string
  'aria-labelledby'?: string
  'aria-describedby'?: string
  'aria-invalid'?: boolean
}

export const Select = ({
  options,
  value,
  onValueChange,
  name,
  disabled,
  required,
  placeholder = 'Selecione uma opção',
  className = '',
  ...props
}: SelectProps) => (
  <SelectPrimitive.Root<string>
    value={value}
    onValueChange={onValueChange}
    name={name}
    disabled={disabled}
    required={required}
    items={options}
  >
    <SelectPrimitive.Trigger
      {...props}
      className={`flex min-h-11 w-full items-center justify-between rounded-md border border-control-border bg-muted px-3 text-left text-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/20 focus-visible:outline-none disabled:opacity-50 ${className}`}
    >
      <SelectPrimitive.Value placeholder={placeholder} />
      <SelectPrimitive.Icon aria-hidden='true'>⌄</SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
    <SelectPrimitive.Portal>
      <SelectPrimitive.Positioner
        className='z-50'
        sideOffset={4}
        alignItemWithTrigger={false}
      >
        <SelectPrimitive.Popup className='max-h-[min(20rem,var(--available-height))] min-w-[var(--anchor-width)] max-w-[var(--available-width)] overflow-y-auto rounded-md border border-control-border bg-card p-1 shadow-card'>
          {options.map((option) => (
            <SelectPrimitive.Item
              key={option.value}
              value={option.value}
              label={option.label}
              className='min-h-11 cursor-default rounded px-3 py-2 text-sm text-foreground outline-none data-highlighted:bg-muted data-selected:font-semibold'
            >
              <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
            </SelectPrimitive.Item>
          ))}
        </SelectPrimitive.Popup>
      </SelectPrimitive.Positioner>
    </SelectPrimitive.Portal>
  </SelectPrimitive.Root>
)
