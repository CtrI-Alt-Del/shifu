export type ChartDotProps = {
  cx?: number
  cy?: number
  isPartial: boolean
  isLast: boolean
}

// Partial estimates are hollow; the latest point is the filled end marker.
export const ChartDot = ({ cx, cy, isPartial, isLast }: ChartDotProps) => {
  if (cx === undefined || cy === undefined || (!isPartial && !isLast)) return null

  return (
    <circle
      cx={cx}
      cy={cy}
      fill={isPartial ? 'var(--card)' : 'var(--jade-text)'}
      r={5}
      stroke={isPartial ? 'var(--jade-text)' : 'var(--card)'}
      strokeWidth={2}
    />
  )
}
