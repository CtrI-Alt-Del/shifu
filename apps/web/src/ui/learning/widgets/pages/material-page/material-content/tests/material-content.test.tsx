import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { MaterialContent } from '..'

describe('MaterialContent', () => {
  afterEach(() => {
    cleanup()
  })

  it('renders every markdown paragraph in its original order', () => {
    render(<MaterialContent content={'Primeiro parágrafo.\n\nSegundo parágrafo.'} />)

    const paragraphs = screen.getAllByText(/parágrafo\./)

    expect(paragraphs).toHaveLength(2)
    expect(paragraphs[0]).toHaveTextContent('Primeiro parágrafo.')
    expect(paragraphs[1]).toHaveTextContent('Segundo parágrafo.')
  })

  it('joins wrapped lines of the same paragraph into one block', () => {
    render(<MaterialContent content={'Uma frase\nque continua na linha seguinte.'} />)

    expect(screen.getByText('Uma frase que continua na linha seguinte.')).toBeVisible()
  })

  it('labels a fenced code block with its language and preserves indentation', () => {
    render(
      <MaterialContent
        content={'Exemplo:\n\n```python\nfor n in [1]:\n    print(n)\n```'}
      />,
    )

    const block = screen.getByRole('region', { name: 'Bloco de código em python' })

    expect(block).toBeVisible()
    expect(block).toHaveTextContent('for n in [1]:')
    expect(block.textContent).toContain('    print(n)')
  })

  it('labels an unfenced-language code block generically', () => {
    render(<MaterialContent content={'```\nvalor = 1\n```'} />)

    expect(screen.getByRole('region', { name: 'Bloco de código' })).toHaveTextContent(
      'valor = 1',
    )
  })

  it('makes a scrollable code block reachable by keyboard', () => {
    render(<MaterialContent content={'```python\nprint(1)\n```'} />)

    expect(
      screen.getByRole('region', { name: 'Bloco de código em python' }),
    ).toHaveAttribute('tabindex', '0')
  })

  it('renders inline code without breaking the surrounding sentence', () => {
    const { container } = render(
      <MaterialContent content='O laço `for` percorre a lista.' />,
    )

    const paragraph = container.querySelector('p')

    expect(paragraph).toHaveTextContent('O laço for percorre a lista.')
    expect(paragraph?.querySelector('code')).toHaveTextContent('for')
  })

  it('shows embedded HTML as literal text instead of interpreting it', () => {
    const content = 'Atenção: <img src=x onerror="alert(1)"> e <b>negrito</b>.'

    const { container } = render(<MaterialContent content={content} />)

    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('b')).toBeNull()
    expect(screen.getByText(content)).toBeVisible()
  })

  it('does not interpret HTML that is nested inside a code block', () => {
    const { container } = render(
      <MaterialContent content={'```html\n<script>alert(1)</script>\n```'} />,
    )

    expect(container.querySelector('script')).toBeNull()
    expect(
      screen.getByRole('region', { name: 'Bloco de código em html' }),
    ).toHaveTextContent('<script>alert(1)</script>')
  })

  it('ignores blank leading and trailing lines', () => {
    const { container } = render(<MaterialContent content={'\n\n\nSó isto.\n\n\n'} />)

    expect(container.querySelectorAll('p')).toHaveLength(1)
    expect(screen.getByText('Só isto.')).toBeVisible()
  })

  it('renders long content as a single constrained reading column', () => {
    const { container } = render(
      <MaterialContent
        content={Array.from({ length: 40 }, (_, i) => `L${i}.`).join('\n\n')}
      />,
    )

    expect(container.querySelectorAll('p')).toHaveLength(40)
    expect(container.firstElementChild).toHaveClass('max-w-[68ch]')
  })
})
