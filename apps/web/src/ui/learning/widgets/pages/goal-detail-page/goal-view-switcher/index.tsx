import type { GoalDetailView } from '../use-goal-detail-page'
import { Tabs, TabsList, TabsTrigger } from '@/ui/shadcn/tabs'

export type GoalViewSwitcherProps = {
  view: GoalDetailView
  onViewChange: (view: string) => void
}

export const GoalViewSwitcher = ({ view, onViewChange }: GoalViewSwitcherProps) => (
  <div>
    <Tabs onValueChange={onViewChange} value={view}>
      <TabsList aria-label='Modo de visualização das Habilidades' className='border-0'>
        <TabsTrigger value='graph'>Grafo</TabsTrigger>
        <TabsTrigger value='list'>Lista</TabsTrigger>
      </TabsList>
    </Tabs>
  </div>
)
