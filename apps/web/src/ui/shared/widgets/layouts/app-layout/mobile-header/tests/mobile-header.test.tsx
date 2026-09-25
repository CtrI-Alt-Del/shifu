import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import type { IconProps } from '@/ui/shared/widgets/components/icon'

import { MobileHeader } from '..'
import { APP_NAVIGATION_ITEMS } from '../../use-app-layout'
import { useMobileHeader } from '../use-mobile-header'

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

vi.mock('../use-mobile-header', () => ({
  useMobileHeader: vi.fn(),
}))

const useMobileHeaderMock = vi.mocked(useMobileHeader)
const handleMenuToggleMock = vi.fn()
const handleNavigationMock = vi.fn()

describe('MobileHeader', () => {
  afterEach(cleanup)

  beforeEach(() => {
    handleMenuToggleMock.mockReset()
    handleNavigationMock.mockReset()
    useMobileHeaderMock.mockReturnValue({
      handleMenuToggle: handleMenuToggleMock,
      handleNavigation: handleNavigationMock,
      isMenuOpen: false,
      menuRef: { current: null },
    })
  })

  it('renders the closed menu control with the current navigation semantics', () => {
    render(<MobileHeader items={APP_NAVIGATION_ITEMS} pathname={ROUTES.root} />)

    const menuButton = screen.getByRole('button', { name: 'Abrir menu' })
    expect(menuButton).toHaveAttribute('aria-controls', 'mobile-navigation')
    expect(menuButton).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('link', { name: 'Shifu — Objetivos' })).toHaveAttribute(
      'href',
      ROUTES.root,
    )
    expect(screen.queryByRole('navigation', { name: 'Navegação móvel' })).toBeNull()

    fireEvent.click(menuButton)
    expect(handleMenuToggleMock).toHaveBeenCalledOnce()
  })

  it('renders an open menu and delegates destination selection', () => {
    useMobileHeaderMock.mockReturnValue({
      handleMenuToggle: handleMenuToggleMock,
      handleNavigation: handleNavigationMock,
      isMenuOpen: true,
      menuRef: { current: null },
    })

    render(<MobileHeader items={APP_NAVIGATION_ITEMS} pathname='/gamification' />)

    const menuButton = screen.getByRole('button', { name: 'Fechar menu' })
    expect(menuButton).toHaveAttribute('aria-expanded', 'true')

    const navigation = screen.getByRole('navigation', { name: 'Navegação móvel' })
    expect(within(navigation).getByRole('link', { name: 'Progresso' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    fireEvent.click(within(navigation).getByRole('link', { name: 'Mentor' }))
    expect(handleNavigationMock).toHaveBeenCalledOnce()
  })

  it('renders account access beside mobile navigation without replacing the menu control', () => {
    render(
      <MobileHeader
        accountMenu={<button type='button'>Conta</button>}
        items={APP_NAVIGATION_ITEMS}
        pathname={ROUTES.root}
      />,
    )

    expect(screen.getByRole('button', { name: 'Conta' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Abrir menu' })).toBeVisible()
  })
})
