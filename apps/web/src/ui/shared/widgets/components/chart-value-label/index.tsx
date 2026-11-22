// Props Recharts passes to a custom label: the position it computed for the
// chosen placement and the value the list's accessor returned.
export type ChartValueLabelProps = {
  x?: number | string
  y?: number | string
  value?: number | string
  // Extra pixels to raise the text above the anchor, to clear a marker.
  lift?: number
}

// Draws the highlighted value on one line, whatever the width of its bar.
export const ChartValueLabel = ({ x, y, value, lift = 0 }: ChartValueLabelProps) => {
  if (value === undefined || value === null || value === '') return null

  return (
    <text
      fill='var(--foreground)'
      fontSize={13}
      fontWeight={600}
      textAnchor='middle'
      x={x}
      y={Number(y) - lift}
    >
      {value}
    </text>
  )
}
