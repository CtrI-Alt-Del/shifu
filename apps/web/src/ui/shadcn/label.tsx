import type { LabelHTMLAttributes } from 'react'

export type LabelProps = LabelHTMLAttributes<HTMLLabelElement> & {
  htmlFor: string
}

export const Label = ({ className = '', htmlFor, ...props }: LabelProps) => {
  return (
    // biome-ignore lint/a11y/noLabelWithoutControl: The primitive receives its association from the consumer.
    <label
      className={`text-sm font-semibold text-foreground ${className}`}
      htmlFor={htmlFor}
      {...props}
    />
  )
}
