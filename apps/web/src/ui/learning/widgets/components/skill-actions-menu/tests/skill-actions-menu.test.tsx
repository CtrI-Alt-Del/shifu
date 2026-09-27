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
})
