import type { RouteName } from '@/constants/routes'
import { Anchor } from '@/ui/shared/widgets/components/anchor'

const SECTIONS: { route: RouteName; label: string }[] = [
  { route: 'accountProfile', label: 'Perfil' },
  { route: 'accountSecurity', label: 'Segurança' },
  { route: 'accountAiUsage', label: 'Uso da IA' },
  { route: 'accountDelete', label: 'Excluir conta' },
]

export const AccountNavigation = () => {
  return (
    // Each section is its own route, so the bar is navigation rather than ARIA
    // tabs; the router marks the current link with `aria-current="page"` and
    // `data-status="active"`. The classes mirror the shared Tabs primitives so
    // the bar keeps the appearance approved in the account page design.
    // - The 3 px padding plus the 1 px border give the board's 4 px inset and
    //   52 px strip.
    // - The `!` border color keeps the board's brighter border, because the global
    //   `* { border-color }` rule outranks layered utilities.
    // - The tabs tighten to 8 px on phones so all four fit in 390 px.
    <nav aria-label='Configurações da conta'>
      <ul className='inline-flex max-w-full gap-1 overflow-x-auto rounded-md border border-control-border! bg-muted p-[3px]'>
        {SECTIONS.map((section) => (
          <li className='shrink-0' key={section.route}>
            <Anchor
              className='inline-flex min-h-11 items-center rounded px-2 text-sm sm:px-3 font-semibold text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-card data-[status=active]:text-foreground'
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
