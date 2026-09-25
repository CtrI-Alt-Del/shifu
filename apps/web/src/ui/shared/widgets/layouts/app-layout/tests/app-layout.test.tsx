import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import type { IconProps } from '@/ui/shared/widgets/components/icon'
import { AppLayout } from '..'
import { useMobileHeader } from '../mobile-header/use-mobile-header'
import { APP_NAVIGATION_ITEMS, useAppLayout } from '../use-app-layout'

vi.mock('../use-app-layout', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../use-app-layout')>()

  return {
    ...actual,
    useAppLayout: vi.fn(),
  }
})

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

vi.mock('../mobile-header/use-mobile-header', () => ({
  useMobileHeader: vi.fn(),
}))

const useAppLayoutMock = vi.mocked(useAppLayout)
const useMobileHeaderMock = vi.mocked(useMobileHeader)
const handleMenuToggleMock = vi.fn()
const handleNavigationMock = vi.fn()

describe('AppLayout', () => {
  afterEach(cleanup)

  beforeEach(() => {
    handleMenuToggleMock.mockReset()
    handleNavigationMock.mockReset()
    useAppLayoutMock.mockReturnValue({
      navigationItems: APP_NAVIGATION_ITEMS,
      pathname: ROUTES.root,
    })
    useMobileHeaderMock.mockReturnValue({
      handleMenuToggle: handleMenuToggleMock,
      handleNavigation: handleNavigationMock,
      isMenuOpen: false,
      menuRef: { current: null },
    })
  })

  it('renders the shared destinations and marks the current destination accessibly', () => {
    render(
      <AppLayout>
        <p>Page content</p>
      </AppLayout>,
    )

    expect(screen.getByRole('link', { name: 'Objetivos' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: 'Progresso' })).toHaveAttribute(
      'href',
      '/gamification',
    )
    expect(screen.getByRole('link', { name: 'Mentor' })).toHaveAttribute(
      'href',
      '/intelligence',
    )
    expect(screen.getByText('Page content')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Abrir menu da conta' })).toBeVisible()
  })

  it('shares the account menu placement across desktop and mobile headers', () => {
    const accountMenu = <button type='button'>Conta compartilhada</button>

    render(<AppLayout accountMenu={accountMenu} />)

    expect(screen.getAllByRole('button', { name: 'Conta compartilhada' })).toHaveLength(2)
    expect(screen.queryByRole('button', { name: 'Abrir menu da conta' })).toBeNull()
  })

  it('renders the open mobile navigation and delegates destination selection', () => {
    useMobileHeaderMock.mockReturnValue({
      handleMenuToggle: handleMenuToggleMock,
      handleNavigation: handleNavigationMock,
      isMenuOpen: true,
      menuRef: { current: null },
    })
    render(<AppLayout />)

    const mobileNavigation = screen.getByRole('navigation', { name: 'Navegação móvel' })
    expect(mobileNavigation).toBeVisible()
    fireEvent.click(within(mobileNavigation).getByRole('link', { name: 'Mentor' }))
    expect(handleNavigationMock).toHaveBeenCalledOnce()
  })

  it('delegates mobile menu toggling to the widget hook', () => {
    render(<AppLayout />)

    fireEvent.click(screen.getByRole('button', { name: 'Abrir menu' }))
    expect(handleMenuToggleMock).toHaveBeenCalledOnce()
  })
})
