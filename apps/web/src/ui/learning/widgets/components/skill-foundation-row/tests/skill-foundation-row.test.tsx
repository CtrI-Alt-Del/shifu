import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, it, expect, vi } from 'vitest'
import { SkillFoundationRow } from '../index'

describe('SkillFoundationRow', () => {
  afterEach(cleanup)

  describe('read-only mode (catalog)', () => {
    it('renders foundation name and status as present', () => {
      render(<SkillFoundationRow skillId='f1' name='HTML Basics' status='present' />)

      expect(screen.getByText('HTML Basics')).toBeInTheDocument()
      expect(screen.getByText(/✓ Presente/)).toBeInTheDocument()
    })

    it('renders foundation status as missing', () => {
      render(<SkillFoundationRow skillId='f1' name='CSS Basics' status='missing' />)

      expect(screen.getByText('CSS Basics')).toBeInTheDocument()
      expect(screen.getByText(/○ Ausente/)).toBeInTheDocument()
    })

    it('does not show checkbox in read-only mode', () => {
      render(
        <SkillFoundationRow
          skillId='f1'
          name='Test Foundation'
          status='present'
          isSelectable={false}
        />,
      )

      const checkbox = screen.queryByRole('checkbox')
      expect(checkbox).not.toBeInTheDocument()
    })
  })

  describe('selectable mode (dialog)', () => {
    it('renders with checkbox and can toggle selection', async () => {
      const onToggle = vi.fn()
      const user = userEvent.setup()

      render(
        <SkillFoundationRow
          skillId='f1'
          name='Selected Foundation'
          status='missing'
          isSelectable={true}
          isSelected={false}
          onToggle={onToggle}
        />,
      )

      const checkbox = screen.getByRole('checkbox')
      expect(checkbox).not.toBeChecked()

      await user.click(checkbox)
      expect(onToggle).toHaveBeenCalledWith('f1')
    })

    it('shows selected state correctly', () => {
      render(
        <SkillFoundationRow
          skillId='f1'
          name='Selected Foundation'
          status='present'
          isSelectable={true}
          isSelected={true}
        />,
      )

      const checkbox = screen.getByRole('checkbox') as HTMLInputElement
      expect(checkbox.checked).toBe(true)
    })

    it('toggles on row click', async () => {
      const onToggle = vi.fn()
      const user = userEvent.setup()

      const { rerender } = render(
        <SkillFoundationRow
          skillId='f1'
          name='Clickable Foundation'
          status='missing'
          isSelectable={true}
          isSelected={false}
          onToggle={onToggle}
        />,
      )

      const row = screen.getByText('Clickable Foundation').closest('label')
      expect(row).not.toBeNull()
      await user.click(row as HTMLLabelElement)
      expect(onToggle).toHaveBeenCalledWith('f1')

      rerender(
        <SkillFoundationRow
          skillId='f1'
          name='Clickable Foundation'
          status='missing'
          isSelectable={true}
          isSelected={true}
          onToggle={onToggle}
        />,
      )

      const checkbox = screen.getByRole('checkbox') as HTMLInputElement
      expect(checkbox.checked).toBe(true)
    })
  })

  describe('status display', () => {
    it('styles present status in green', () => {
      render(
        <SkillFoundationRow
          skillId='f1'
          name='Test'
          status='present'
          isSelectable={false}
        />,
      )

      const statusElement = screen.getByText(/✓ Presente/)
      expect(statusElement).toHaveClass('text-green-600')
    })

    it('styles missing status in gray', () => {
      render(
        <SkillFoundationRow
          skillId='f1'
          name='Test'
          status='missing'
          isSelectable={false}
        />,
      )

      const statusElement = screen.getByText(/○ Ausente/)
      expect(statusElement).toHaveClass('text-gray-500')
    })
  })
})
