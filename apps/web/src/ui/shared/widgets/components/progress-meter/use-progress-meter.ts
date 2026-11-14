import { useReducedMotionPreference } from '@/ui/shared/hooks/use-reduced-motion-preference'

import type { ProgressMeterProps } from '.'

export function useProgressMeter({ tone = 'primary', value }: ProgressMeterProps) {
  const { prefersReducedMotion } = useReducedMotionPreference()
  const boundedValue = Math.min(100, Math.max(0, value))

  return {
    boundedValue,
    displayValue: Math.round(boundedValue),
    toneClassName: tone === 'success' ? 'text-success' : 'text-primary',
    fillClassName: tone === 'success' ? 'bg-success' : 'bg-primary',
    // The meter can render outside an entrance tree, so it grows from empty on
    // its own; with reduced motion it shows its final width on first paint.
    fillInitial: prefersReducedMotion ? (false as const) : { width: '0%' },
  }
}
