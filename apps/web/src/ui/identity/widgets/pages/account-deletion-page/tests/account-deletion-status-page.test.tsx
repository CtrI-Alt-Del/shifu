import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { AccountErasureResult } from '@/rest/services/identity-service'
import { AccountDeletionStatusPage } from '..'

const baseStatus: AccountErasureResult = {
  state: 'closed',
  closed_at: '2026-11-21T12:00:00Z',
  erasure: 'pending',
}

describe('AccountDeletionStatusPage', () => {
  afterEach(cleanup)

  it.each([
    ['pending', 'Eliminação em andamento'],
    ['completed', 'Eliminação concluída'],
  ] as const)('explains a closed account with %s erasure', (erasure, heading) => {
    render(<AccountDeletionStatusPage status={{ ...baseStatus, erasure }} />)

    expect(
      screen.getByRole('heading', { level: 1, name: 'Conta encerrada' }),
    ).toBeVisible()
    expect(screen.getByRole('heading', { level: 2, name: heading })).toBeVisible()
    expect(
      screen.getByText(/Dados guardados em um navegador que ficou desconectado/),
    ).toBeVisible()
  })
})
