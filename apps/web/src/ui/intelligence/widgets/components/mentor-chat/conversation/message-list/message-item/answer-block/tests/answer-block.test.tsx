import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AnswerBlock } from '..'
import { useAnswerBlock } from '../use-answer-block'

vi.mock('../use-answer-block', () => ({ useAnswerBlock: vi.fn() }))
const useAnswerBlockMock = vi.mocked(useAnswerBlock)

const TABLE = [
  'Como exemplo ilustrativo:',
  '',
  '| | Exemplo | Analogia |',
  '|---|---|---|',
  '| **Habilidade** | Resolver problemas de multiplicação | O destino de uma viagem |',
  '| **Competência** | Representar uma multiplicação como adição | Uma etapa do caminho |',
].join('\n')

describe('AnswerBlock', () => {
  beforeEach(() => {
    useAnswerBlockMock.mockReturnValue({ resolveLink: () => ({ kind: 'text' }) })
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('renders a Markdown table as a table instead of pipe-separated text', () => {
    render(<AnswerBlock content={TABLE} />)

    const table = screen.getByRole('table')
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((cell) => cell.textContent),
    ).toEqual(['', 'Exemplo', 'Analogia'])
    const rows = within(table).getAllByRole('row')
    expect(rows).toHaveLength(3)
    expect(
      within(rows[1])
        .getAllByRole('cell')
        .map((cell) => cell.textContent),
    ).toEqual([
      'Habilidade',
      'Resolver problemas de multiplicação',
      'O destino de uma viagem',
    ])
    expect(screen.queryByText(/\|---/)).toBeNull()
  })

  it('keeps a wide table scrollable by keyboard inside the answer', () => {
    render(<AnswerBlock content={TABLE} />)

    const region = screen.getByRole('region', { name: 'Tabela' })
    const scroller = within(region).getByRole('table').parentElement
    expect(scroller).toHaveAttribute('tabindex', '0')
    expect(scroller).toHaveClass('overflow-x-auto')
  })

  it('renders struck-through text from the GitHub Markdown extension', () => {
    render(<AnswerBlock content='Use ~~var~~ `let` no lugar.' />)

    expect(screen.getByText('var').tagName).toBe('DEL')
  })
})
