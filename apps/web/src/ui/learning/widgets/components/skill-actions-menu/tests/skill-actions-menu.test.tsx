import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SkillActionsMenu } from '..'

describe('SkillActionsMenu', () => {
  afterEach(cleanup)
  it('opens from an accessible neutral trigger and selects removal', async () => {
    const user = userEvent.setup()
    const onRemove = vi.fn()
    render(<SkillActionsMenu onRemove={onRemove} skillName='Lógica' />)

    await user.click(screen.getByRole('button', { name: 'Mais ações de Lógica' }))
    await user.click(screen.getByRole('menuitem', { name: 'Remover habilidade' }))

    expect(onRemove).toHaveBeenCalledOnce()
  })

  it('closes with Escape and restores focus to the trigger', async () => {
    const user = userEvent.setup()
    render(<SkillActionsMenu onRemove={vi.fn()} skillName='Lógica' />)
    const trigger = screen.getByRole('button', { name: 'Mais ações de Lógica' })

    await user.click(trigger)
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('menuitem')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  // Class presence is asserted only because the surface size is visual-only,
  // with no semantic equivalent to query.
  it.each([
    [undefined, 'inset-1', 'border-control-border'],
    ['inset' as const, 'inset-1', 'border-control-border'],
    ['full' as const, 'inset-0', 'border-control-border!'],
  ])(
    'draws the visible surface with %s as %s inside the 44 px target',
    (surface, expectedClass, expectedBorderClass) => {
      render(<SkillActionsMenu onRemove={vi.fn()} skillName='Lógica' surface={surface} />)
      const trigger = screen.getByRole('button', { name: 'Mais ações de Lógica' })
      const surfaceElement = trigger.querySelector('span[aria-hidden="true"]')

      expect(trigger).toHaveClass('size-11')
      expect(surfaceElement).toHaveClass(expectedClass)
      expect(surfaceElement).toHaveClass(expectedBorderClass)
    },
  )
})
