import { Switch as SwitchPrimitive } from '@base-ui/react/switch'

export type SwitchProps = {
  id?: string
  name?: string
  className?: string
  checked: boolean
  disabled?: boolean
  onCheckedChange: (checked: boolean) => void
  'aria-label'?: string
  'aria-labelledby'?: string
  'aria-describedby'?: string
}

export const Switch = ({
  checked,
  onCheckedChange,
  className = '',
  ...props
}: SwitchProps) => (
  <SwitchPrimitive.Root
    {...props}
    checked={checked}
    onCheckedChange={onCheckedChange}
    className={`inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-transparent bg-muted px-0.5 transition-colors data-[checked]:bg-jade-fill data-[unchecked]:border-control-border disabled:cursor-not-allowed data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${className}`}
  >
    <SwitchPrimitive.Thumb className='pointer-events-none block size-5 rounded-full bg-muted-foreground transition-transform data-[checked]:translate-x-5 data-[checked]:bg-on-jade' />
  </SwitchPrimitive.Root>
)
