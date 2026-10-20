import { TabsList, TabsTrigger } from '@/ui/shadcn/tabs'

export type GamificationTab = 'calendario' | 'conquistas'

const TABS: { value: GamificationTab; label: string }[] = [
  { value: 'calendario', label: 'Calendário' },
  { value: 'conquistas', label: 'Conquistas' },
]

export const GamificationTabs = () => {
  return (
    // The shadcn primitive ships a segmented box with its own active colours;
    // the design is a plain row with a bottom divider and a latao active tab.
    // `!` is required because the primitive's `data-[state=active]:` variants
    // outrank a plain utility class.
    <TabsList className='w-full justify-start gap-2 rounded-none! border-0! border-b! border-border! bg-transparent! p-0! pb-4!'>
      {TABS.map((tab) => (
        <TabsTrigger
          className='h-11 rounded-[10px] px-4 text-muted-foreground data-[state=active]:bg-latao-tint! data-[state=active]:text-latao-text!'
          key={tab.value}
          value={tab.value}
        >
          {tab.label}
        </TabsTrigger>
      ))}
    </TabsList>
  )
}
