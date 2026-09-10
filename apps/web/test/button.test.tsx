import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Button } from '@/ui/shadcn/components/button'

describe('Button', () => {
  it('renders default button with text', () => {
    render(<Button>Entrar no Dojo</Button>)
    expect(screen.getByRole('button', { name: /entrar no dojo/i })).toBeInTheDocument()
  })

  it('renders jade variant for learning feedback', () => {
    render(<Button variant='jade'>Concluir Competência</Button>)
    expect(
      screen.getByRole('button', { name: /concluir competência/i }),
    ).toBeInTheDocument()
  })
})
