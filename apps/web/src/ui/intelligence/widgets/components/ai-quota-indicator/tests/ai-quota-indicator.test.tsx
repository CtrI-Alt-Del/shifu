import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'
import type { IconProps } from '@/ui/shared/widgets/components/icon'

import { AiQuotaIndicator } from '..'
import { useAiQuotaIndicator } from '../use-ai-quota-indicator'

vi.mock('../use-ai-quota-indicator', () => ({
  useAiQuotaIndicator: vi.fn(),
}))

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

vi.mock('@/ui/shared/widgets/components/icon', () => ({
  Icon: ({ name }: IconProps) => <span data-icon={name} />,
}))

const useAiQuotaIndicatorMock = vi.mocked(useAiQuotaIndicator)

function createState(
  overrides: Partial<ReturnType<typeof useAiQuotaIndicator>> = {},
): ReturnType<typeof useAiQuotaIndicator> {
  return {
    isVisible: true,
    text: 'IA · 42%',
    label: 'Uso da IA: 42% da cota mensal',
    iconName: null,
    toneClassName: 'text-muted-foreground',
    ...overrides,
  }
}

describe('AiQuotaIndicator', () => {
  afterEach(cleanup)

  beforeEach(() => {
    useAiQuotaIndicatorMock.mockReturnValue(createState())
  })

  it('links the percentage to the usage page with the full accessible label', () => {
    render(<AiQuotaIndicator />)

    const indicator = screen.getByRole('link', { name: 'Uso da IA: 42% da cota mensal' })
    expect(indicator).toHaveAttribute('href', ROUTES.accountAiUsage)
    expect(indicator).toHaveTextContent('IA · 42%')
    expect(indicator.querySelector('[data-icon]')).toBeNull()
  })

  it('shows an icon and text for the near-limit and blocked states', () => {
    useAiQuotaIndicatorMock.mockReturnValue(
      createState({
        text: 'IA · 85%',
        label: 'Uso da IA: 85% da cota mensal, perto do limite',
        iconName: 'triangle-alert',
        toneClassName: 'text-selo-text',
      }),
    )
    const { rerender } = render(<AiQuotaIndicator />)

    const nearLimit = screen.getByRole('link', {
      name: 'Uso da IA: 85% da cota mensal, perto do limite',
    })
    expect(nearLimit).toHaveTextContent('IA · 85%')
    expect(nearLimit.querySelector('[data-icon="triangle-alert"]')).not.toBeNull()

    useAiQuotaIndicatorMock.mockReturnValue(
      createState({
        text: 'IA · 100%',
        label: 'Uso da IA: 100% da cota mensal, cota esgotada',
        iconName: 'circle-pause',
        toneClassName: 'text-selo-text',
      }),
    )
    rerender(<AiQuotaIndicator />)

    const blocked = screen.getByRole('link', {
      name: 'Uso da IA: 100% da cota mensal, cota esgotada',
    })
    expect(blocked).toHaveTextContent('IA · 100%')
    expect(blocked.querySelector('[data-icon="circle-pause"]')).not.toBeNull()
  })

  it('shows the unavailable state as a link to the usage page', () => {
    useAiQuotaIndicatorMock.mockReturnValue(
      createState({
        text: 'IA · indisponível',
        label: 'Uso da IA: indisponível no momento',
        iconName: null,
      }),
    )

    render(<AiQuotaIndicator />)

    const indicator = screen.getByRole('link', {
      name: 'Uso da IA: indisponível no momento',
    })
    expect(indicator).toHaveAttribute('href', ROUTES.accountAiUsage)
    expect(indicator).toHaveTextContent('IA · indisponível')
    expect(indicator.querySelector('[data-icon]')).toBeNull()
  })

  it('renders nothing while the first reading loads', () => {
    useAiQuotaIndicatorMock.mockReturnValue(
      createState({ isVisible: false, text: '', label: '' }),
    )

    render(<AiQuotaIndicator />)

    expect(screen.queryByRole('link')).toBeNull()
  })
})
