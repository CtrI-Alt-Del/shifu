import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Icon, type IconName } from '..'

describe('Icon', () => {
  it('renders every competency-detail icon through the shared registry', () => {
    const names: IconName[] = [
      'arrow-left',
      'chevron-right',
      'lock-keyhole',
      'rotate-ccw',
      'target',
    ]

    const { container } = render(
      <div>
        {names.map((name) => (
          <Icon key={name} name={name} />
        ))}
      </div>,
    )

    expect(container.querySelectorAll('svg')).toHaveLength(names.length)
    expect(container.querySelectorAll('svg[aria-hidden="true"]')).toHaveLength(
      names.length,
    )
  })
})
