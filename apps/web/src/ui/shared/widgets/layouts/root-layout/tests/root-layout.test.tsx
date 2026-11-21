import { cleanup, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { RootLayout } from '..'
import { useRootLayout } from '../use-root-layout'

vi.mock('@tanstack/react-router', () => ({
  HeadContent: () => null,
  Scripts: () => null,
}))
vi.mock('../use-root-layout', () => ({
  useRootLayout: vi.fn(),
}))
vi.mock('@/ui/shared/contexts/rest-context', () => ({
  RestContextProvider: ({ children }: { children: ReactNode }) => children,
}))
vi.mock('@/ui/shared/contexts/auth-context', () => ({
  AuthContextProvider: ({ children }: { children: ReactNode }) => children,
}))
vi.mock('@/ui/shadcn/sonner', () => ({
  Toaster: () => <div data-testid='toaster' />,
}))
vi.mock('@/ui/shared/widgets/layouts/app-layout', () => ({
  AppLayout: ({ children }: { children: ReactNode }) => (
    <div data-testid='app-layout'>{children}</div>
  ),
}))

const useRootLayoutMock = vi.mocked(useRootLayout)

describe('RootLayout', () => {
  afterEach(cleanup)

  it('keeps public content outside the authenticated shell', () => {
    useRootLayoutMock.mockReturnValue({
      mentorContextHint: null,
      isHydrated: true,
      isPublic: true,
    })

    render(
      <RootLayout>
        <p>Public content</p>
      </RootLayout>,
    )

    expect(screen.getByText('Public content')).toBeVisible()
    expect(screen.queryByTestId('square-background')).not.toBeInTheDocument()
    expect(screen.queryByTestId('app-layout')).not.toBeInTheDocument()
  })

  it('wraps protected content with the application shell', () => {
    useRootLayoutMock.mockReturnValue({
      mentorContextHint: null,
      isHydrated: true,
      isPublic: false,
    })

    render(
      <RootLayout>
        <p>Protected content</p>
      </RootLayout>,
    )

    expect(screen.getByTestId('app-layout')).toContainElement(
      screen.getByText('Protected content'),
    )
    expect(screen.queryByTestId('square-background')).not.toBeInTheDocument()
  })

  it('keeps the decorative background out of the public and protected shells', () => {
    useRootLayoutMock.mockReturnValue({
      mentorContextHint: null,
      isHydrated: true,
      isPublic: true,
    })

    const { rerender } = render(
      <RootLayout>
        <p>Page content</p>
      </RootLayout>,
    )
    expect(screen.queryByTestId('square-background')).not.toBeInTheDocument()

    useRootLayoutMock.mockReturnValue({
      mentorContextHint: null,
      isHydrated: true,
      isPublic: false,
    })
    rerender(
      <RootLayout>
        <p>Page content</p>
      </RootLayout>,
    )

    expect(screen.queryByTestId('square-background')).not.toBeInTheDocument()
  })

  it.each([
    ['public', true],
    ['protected', false],
  ])('mounts the single toaster on %s routes', (_case, isPublic) => {
    useRootLayoutMock.mockReturnValue({
      mentorContextHint: null,
      isHydrated: true,
      isPublic,
    })

    render(
      <RootLayout>
        <p>Content</p>
      </RootLayout>,
    )

    expect(screen.getAllByTestId('toaster')).toHaveLength(1)
  })
})
