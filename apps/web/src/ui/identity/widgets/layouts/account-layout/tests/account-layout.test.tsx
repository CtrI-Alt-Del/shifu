import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { AccountLayout } from '..'

// The active link state comes from the router (`aria-current="page"`); it is
// asserted by the browser suite against the real routes.
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

describe('AccountLayout', () => {
  afterEach(cleanup)

  it('renders the account title above the routed section', () => {
    render(
      <AccountLayout>
        <p>Conteúdo da seção</p>
      </AccountLayout>,
    )

    expect(screen.getByRole('heading', { level: 1, name: 'Sua conta' })).toBeVisible()
    expect(screen.getByText('Conteúdo da seção')).toBeVisible()
  })

  it('links every account section to its own route, in order, without tab roles', () => {
    render(<AccountLayout />)

    const navigation = screen.getByRole('navigation', { name: 'Configurações da conta' })
    const links = within(navigation).getAllByRole('link')

    expect(links.map((link) => [link.textContent, link.getAttribute('href')])).toEqual([
      ['Perfil', ROUTES.accountProfile],
      ['Segurança', ROUTES.accountSecurity],
      ['Excluir conta', ROUTES.accountDelete],
    ])
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()
  })
})
