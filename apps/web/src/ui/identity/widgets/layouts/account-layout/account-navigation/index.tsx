import type { RouteName } from '@/constants/routes'
import { Anchor } from '@/ui/shared/widgets/components/anchor'

const SECTIONS: { route: RouteName; label: string }[] = [
  { route: 'accountProfile', label: 'Perfil' },
  { route: 'accountSecurity', label: 'Segurança' },
  { route: 'accountDelete', label: 'Excluir conta' },
]

export const AccountNavigation = () => {
  return (
    // Each section is its own route, so the bar is navigation rather than ARIA
    // tabs; the router marks the current link with `aria-current="page"` and
    // `data-status="active"`. The classes mirror the shared Tabs primitives so
    // the bar keeps the appearance approved in the account page design.
    <nav aria-label='Configurações da conta'>
      <ul className='inline-flex min-h-11 max-w-full gap-1 overflow-x-auto rounded-md border border-control-border bg-muted p-1'>
        {SECTIONS.map((section) => (
          <li className='shrink-0' key={section.route}>
            <Anchor
              className='inline-flex min-h-9 items-center rounded px-3 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground data-[status=active]:bg-card data-[status=active]:text-foreground'
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
