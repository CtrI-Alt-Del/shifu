import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import type { IconProps } from '@/ui/shared/widgets/components/icon'

import { MobileBottomNavigation } from '..'
import { APP_NAVIGATION_ITEMS } from '../../use-app-layout'

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

vi.mock('@/ui/shared/widgets/components/icon', () => ({
  Icon: ({ name }: IconProps) => <span aria-hidden='true'>{name}</span>,
}))

describe('MobileBottomNavigation', () => {
  afterEach(cleanup)

  it('renders every bottom destination with accessible labels and routes', () => {
    render(
      <MobileBottomNavigation items={APP_NAVIGATION_ITEMS} pathname='/intelligence' />,
    )

    const navigation = screen.getByRole('navigation', { name: 'Navegação inferior' })

    expect(screen.getAllByRole('link')).toHaveLength(4)
    expect(
      screen.getByRole('link', { name: 'Objetivos — navegação inferior' }),
    ).toHaveAttribute('href', ROUTES.root)
    expect(
      screen.getByRole('link', { name: 'Progresso — navegação inferior' }),
    ).toHaveAttribute('href', ROUTES.gamification)
    expect(
      screen.getByRole('link', { name: 'Mentor — navegação inferior' }),
    ).toHaveAttribute('aria-current', 'page')
    expect(
      screen.getByRole('link', { name: 'Conta — navegação inferior' }),
    ).toHaveAttribute('href', ROUTES.account)
    expect(navigation).toBeVisible()
  })

  it('does not mark unrelated destinations as active', () => {
    render(
      <MobileBottomNavigation
        items={APP_NAVIGATION_ITEMS}
        pathname='/gamification/settings'
      />,
    )

    expect(
      screen.getByRole('link', { name: 'Progresso — navegação inferior' }),
    ).toHaveAttribute('aria-current', 'page')
    expect(
      screen.getByRole('link', { name: 'Objetivos — navegação inferior' }),
    ).not.toHaveAttribute('aria-current')
    expect(
      screen.getByRole('link', { name: 'Mentor — navegação inferior' }),
    ).not.toHaveAttribute('aria-current')
  })
})
