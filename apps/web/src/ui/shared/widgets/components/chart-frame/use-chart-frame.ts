import { useId, useState } from 'react'

export type ChartView = 'chart' | 'table'

export function useChartFrame() {
  const headingId = useId()
  const [view, setView] = useState<ChartView>('chart')

  function handleViewChange(nextView: string) {
    if (nextView === 'chart' || nextView === 'table') setView(nextView)
  }

  return { headingId, view, handleViewChange }
}
