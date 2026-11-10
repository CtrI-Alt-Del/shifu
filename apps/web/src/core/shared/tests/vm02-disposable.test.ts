// Disposable test for the SHIFU-87 VM-02 check. It fails on purpose and is never merged.
import { expect, it } from 'vitest'

it('fails on purpose for the VM-02 check', () => {
  expect(1).toBe(2)
})
