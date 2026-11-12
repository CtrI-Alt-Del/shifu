import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import { useAiQuotaIndicator } from '@/ui/intelligence/widgets/components/ai-quota-indicator/use-ai-quota-indicator'
import type { IconProps } from '@/ui/shared/widgets/components/icon'

import { DesktopHeader } from '..'
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

vi.mock(
  '@/ui/intelligence/widgets/components/ai-quota-indicator/use-ai-quota-indicator',
  () => ({
    useAiQuotaIndicator: vi.fn(),
  }),
)

const useAiQuotaIndicatorMock = vi.mocked(useAiQuotaIndicator)

function createAiQuotaIndicatorState(
  overrides: Partial<ReturnType<typeof useAiQuotaIndicator>> = {},
): ReturnType<typeof useAiQuotaIndicator> {
  return {
    isVisible: true,
    text: 'IA · 85%',
    label: 'Uso da IA: 85% da cota mensal, perto do limite',
    iconName: 'triangle-alert',
    toneClassName: 'text-selo-text',
    ...overrides,
  }
}

describe('DesktopHeader', () => {
  afterEach(cleanup)

  beforeEach(() => {
    useAiQuotaIndicatorMock.mockReturnValue(createAiQuotaIndicatorState())
  })

  it('renders the brand and marks the active primary destination', () => {
    render(<DesktopHeader items={APP_NAVIGATION_ITEMS} pathname='/gamification' />)

    expect(screen.getByRole('link', { name: 'Shifu — Objetivos' })).toHaveAttribute(
      'href',
      ROUTES.root,
    )
    expect(screen.getByRole('link', { name: 'Objetivos' })).toHaveAttribute(
      'href',
      ROUTES.root,
    )
    expect(screen.getByRole('link', { name: 'Progresso' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: 'Mentor' })).toHaveAttribute(
      'href',
      ROUTES.intelligence,
    )
  })

  it('renders the default account trigger and accepts a custom account menu', () => {
    const { rerender } = render(
      <DesktopHeader items={APP_NAVIGATION_ITEMS} pathname={ROUTES.root} />,
    )

    expect(screen.getByRole('button', { name: 'Abrir menu da conta' })).toBeVisible()

    rerender(
      <DesktopHeader
        accountMenu={<button type='button'>Conta personalizada</button>}
        items={APP_NAVIGATION_ITEMS}
        pathname={ROUTES.root}
      />,
    )

    expect(screen.getByRole('button', { name: 'Conta personalizada' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Abrir menu da conta' })).toBeNull()
  })

  it('links the AI quota indicator to the usage page beside the account menu', () => {
    render(<DesktopHeader items={APP_NAVIGATION_ITEMS} pathname={ROUTES.root} />)

    const indicator = screen.getByRole('link', {
      name: 'Uso da IA: 85% da cota mensal, perto do limite',
    })
    expect(indicator).toHaveAttribute('href', ROUTES.accountAiUsage)
    expect(indicator).toHaveTextContent('IA · 85%')
    expect(screen.getByRole('button', { name: 'Abrir menu da conta' })).toBeVisible()
  })

  it('hides the AI quota indicator while the first reading loads', () => {
    useAiQuotaIndicatorMock.mockReturnValue(
      createAiQuotaIndicatorState({ isVisible: false, text: '', label: '' }),
    )

    render(<DesktopHeader items={APP_NAVIGATION_ITEMS} pathname={ROUTES.root} />)

    expect(screen.queryByRole('link', { name: /Uso da IA/ })).toBeNull()
  })
})
