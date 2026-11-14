import { useAnimatedNumber } from './use-animated-number'

export type AnimatedNumberProps = {
  value: number
  format?: (value: number) => string
  duration?: number
  delay?: number
  className?: string
}

// Counts up to `value`; with reduced motion it shows the final figure at once.
export const AnimatedNumber = (props: AnimatedNumberProps) => {
  const { text } = useAnimatedNumber(props)

  return <span className={`tabular-nums ${props.className ?? ''}`}>{text}</span>
}
