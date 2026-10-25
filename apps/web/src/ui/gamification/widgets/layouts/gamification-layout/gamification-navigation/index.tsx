import type { RouteName } from '@/constants/routes'
import { Anchor } from '@/ui/shared/widgets/components/anchor'

const SECTIONS: { route: RouteName; label: string }[] = [
  { route: 'gamificationOverview', label: 'Visão geral' },
  { route: 'gamificationCalendar', label: 'Calendário' },
  { route: 'gamificationAchievements', label: 'Conquistas' },
  { route: 'gamificationXpHistory', label: 'Histórico de XP' },
]

export const GamificationNavigation = () => {
  return (
    // Each section is its own route, so the bar is navigation rather than ARIA
    // tabs; the router marks the current link with `aria-current="page"` and
    // `data-status="active"`, which drives the latao active style.
    // `overflow-x-auto` keeps the fourth link from pushing the whole page wider
    // than the viewport at narrow widths: the bar scrolls, the page does not.
    <nav aria-label='Seções da gamificação'>
      <ul className='flex w-full justify-start gap-2 overflow-x-auto border-b border-border pb-4'>
        {SECTIONS.map((section) => (
          <li className='shrink-0' key={section.route}>
            <Anchor
              className='inline-flex h-11 items-center rounded-[10px] px-4 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-latao-tint data-[status=active]:text-latao-text'
              route={section.route}
            >
              {section.label}
            </Anchor>
          </li>
        ))}
      </ul>
    </nav>
  )
}
