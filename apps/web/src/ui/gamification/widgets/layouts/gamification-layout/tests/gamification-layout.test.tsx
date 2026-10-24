import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { GamificationLayout } from '..'

// The active link state comes from the router (`aria-current="page"`); it is
// asserted by the browser suite against the real routes.
vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

describe('GamificationLayout', () => {
  afterEach(cleanup)

  it('renders the area header above the routed section', () => {
    render(
      <GamificationLayout>
        <p>Conteúdo da seção</p>
      </GamificationLayout>,
    )

    expect(screen.getByRole('heading', { level: 1, name: 'Gamificação' })).toBeVisible()
    expect(
      screen.getByText('Sua constância, seus marcos e o XP que você conquistou.'),
    ).toBeVisible()
    expect(screen.getByText('Conteúdo da seção')).toBeVisible()
  })

  it('links every section to its own route, in order', () => {
    render(<GamificationLayout />)

    const navigation = screen.getByRole('navigation', { name: 'Seções da gamificação' })
    const links = within(navigation).getAllByRole('link')

    expect(links.map((link) => [link.textContent, link.getAttribute('href')])).toEqual([
      ['Visão geral', ROUTES.gamificationOverview],
      ['Calendário', ROUTES.gamificationCalendar],
      ['Conquistas', ROUTES.gamificationAchievements],
      ['Histórico de XP', ROUTES.gamificationXpHistory],
    ])
  })
})
