import type { GoalDetailView } from '../use-goal-detail-page'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { Tabs, TabsList, TabsTrigger } from '@/ui/shadcn/tabs'

export type GoalViewSwitcherProps = {
  view: GoalDetailView
  onViewChange: (view: string) => void
}

export const GoalViewSwitcher = ({ view, onViewChange }: GoalViewSwitcherProps) => (
  <div>
    <Tabs onValueChange={onViewChange} value={view}>
      <TabsList aria-label='Modo de visualização das Habilidades'>
        <TabsTrigger value='graph'>
          <Icon name='network' size={16} /> <span className='ml-2'>Grafo</span>
        </TabsTrigger>
        <TabsTrigger value='list'>
          <Icon name='menu' size={16} /> <span className='ml-2'>Lista</span>
        </TabsTrigger>
      </TabsList>
    </Tabs>
  </div>
)
