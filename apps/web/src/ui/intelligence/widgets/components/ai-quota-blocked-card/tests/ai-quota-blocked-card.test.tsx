import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ROUTES } from '@/constants/routes'
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

import { AiQuotaBlockedCard } from '..'

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {typeof children === 'function' ? children({ isActive: false }) : children}
    </a>
  ),
}))

describe('AiQuotaBlockedCard', () => {
  afterEach(cleanup)

  it('explains the block as a status with the id that blocked controls describe', () => {
    render(<AiQuotaBlockedCard id='quota-blocked' message='A cota acabou.' />)

    const card = screen.getByRole('status')
    expect(card).toHaveAttribute('id', 'quota-blocked')
    expect(card).toHaveTextContent('A cota acabou.')
    expect(screen.getByRole('link', { name: 'Ver uso da IA' })).toHaveAttribute(
      'href',
      ROUTES.accountAiUsage,
    )
  })

  it('becomes an alert right after a refusal', () => {
    render(
      <AiQuotaBlockedCard id='quota-blocked' message='A cota acabou.' role='alert' />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('A cota acabou.')
    expect(screen.queryByRole('status')).toBeNull()
  })
})
