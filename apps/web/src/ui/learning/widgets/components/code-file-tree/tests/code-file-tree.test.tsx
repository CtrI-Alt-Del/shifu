import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CodeFileTree } from '..'

describe('CodeFileTree', () => {
  afterEach(cleanup)

  it('opens nested files and selects a file without offering project mutations', () => {
    const onSelectFile = vi.fn()
    render(
      <CodeFileTree
        files={[{ path: 'src/main.js' }, { path: 'src/helper.js' }]}
        selectedPath='src/main.js'
        editablePaths={['src/main.js']}
        onSelectFile={onSelectFile}
      />,
    )

    expect(screen.getByRole('tree', { name: 'Arquivos do projeto' })).toBeVisible()
    expect(screen.getByRole('treeitem', { name: 'src' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(screen.getByRole('treeitem', { name: 'main.js' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    fireEvent.click(screen.getByRole('treeitem', { name: 'helper.js' }))
    expect(onSelectFile).toHaveBeenCalledWith('src/helper.js')
    expect(
      screen.queryByRole('button', { name: /novo arquivo|renomear|excluir/i }),
    ).not.toBeInTheDocument()
  })
})
