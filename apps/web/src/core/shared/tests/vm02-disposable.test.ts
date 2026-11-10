// Disposable test for the SHIFU-87 VM-02 check. It covers only part of the code.
import { expect, it } from 'vitest'

import { vm02Clamp, vm02Sign } from '../vm02-disposable'

it('clamps a value inside a range', () => {
  expect(vm02Clamp(5, 0, 10)).toBe(5)
  expect(vm02Clamp(-1, 0, 10)).toBe(0)
})

it('returns the sign of a value', () => {
  expect(vm02Sign(3)).toBe(1)
})
