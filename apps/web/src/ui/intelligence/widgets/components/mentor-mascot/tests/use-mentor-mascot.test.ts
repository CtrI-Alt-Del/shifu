import { act, render, waitFor } from '@testing-library/react'
import { useReducedMotion } from 'motion/react'
import { createElement } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useMentorMascot } from '../use-mentor-mascot'

const lottie = vi.hoisted(() => ({ loadAnimation: vi.fn() }))

vi.mock('lottie-web/build/player/lottie_light', () => ({ default: lottie }))
vi.mock('motion/react', async (importOriginal) => ({
  ...(await importOriginal<typeof import('motion/react')>()),
  useReducedMotion: vi.fn(() => false),
}))

const useReducedMotionMock = vi.mocked(useReducedMotion)

type AnimationListener = () => void

function createAnimationStub() {
  const listeners = new Map<string, AnimationListener>()
  return {
    totalFrames: 108,
    addEventListener: vi.fn((name: string, listener: AnimationListener) => {
      listeners.set(name, listener)
    }),
    goToAndStop: vi.fn(),
    destroy: vi.fn(),
    emit(name: string) {
      listeners.get(name)?.()
    },
  }
}

let hookResult: ReturnType<typeof useMentorMascot>

function Harness({ isAnimated }: { isAnimated: boolean }) {
  hookResult = useMentorMascot({ isAnimated })
  return createElement('div', { ref: hookResult.containerRef })
}

function renderHarness(isAnimated = true) {
  return render(createElement(Harness, { isAnimated }))
}

describe('useMentorMascot', () => {
  let animation: ReturnType<typeof createAnimationStub>

  beforeEach(() => {
    animation = createAnimationStub()
    lottie.loadAnimation.mockReset().mockReturnValue(animation)
    useReducedMotionMock.mockReturnValue(false)
  })

  it('plays the greeting once inside the mounted container', async () => {
    const { container } = renderHarness()

    await waitFor(() => expect(lottie.loadAnimation).toHaveBeenCalledTimes(1))
    expect(lottie.loadAnimation).toHaveBeenCalledWith(
      expect.objectContaining({
        container: container.firstChild,
        renderer: 'svg',
        loop: false,
        autoplay: true,
        path: expect.stringContaining(
          'studio/public/projects/mascot/scene-1/lottie.json',
        ),
      }),
    )
    expect(animation.goToAndStop).not.toHaveBeenCalled()
    expect(hookResult.hasFailed).toBe(false)
  })

  it('shows the settled mascot without playing when it is static', async () => {
    renderHarness(false)

    await waitFor(() => expect(lottie.loadAnimation).toHaveBeenCalledTimes(1))
    expect(lottie.loadAnimation).toHaveBeenCalledWith(
      expect.objectContaining({ autoplay: false }),
    )

    act(() => animation.emit('DOMLoaded'))

    expect(animation.goToAndStop).toHaveBeenCalledWith(107, true)
  })

  it('shows the settled mascot without the entrance when motion is reduced', async () => {
    useReducedMotionMock.mockReturnValue(true)
    renderHarness()

    await waitFor(() => expect(lottie.loadAnimation).toHaveBeenCalledTimes(1))
    expect(lottie.loadAnimation).toHaveBeenCalledWith(
      expect.objectContaining({ autoplay: false }),
    )

    act(() => animation.emit('DOMLoaded'))

    expect(animation.goToAndStop).toHaveBeenCalledWith(107, true)
  })

  it('reports a failure when the animation data cannot be loaded', async () => {
    renderHarness()
    await waitFor(() => expect(lottie.loadAnimation).toHaveBeenCalledTimes(1))

    act(() => animation.emit('data_failed'))

    expect(hookResult.hasFailed).toBe(true)
  })

  it('reports a failure when the player cannot start', async () => {
    lottie.loadAnimation.mockImplementation(() => {
      throw new Error('player unavailable')
    })
    renderHarness()

    await waitFor(() => expect(hookResult.hasFailed).toBe(true))
  })

  it('destroys the animation when the mascot unmounts', async () => {
    const { unmount } = renderHarness()
    await waitFor(() => expect(lottie.loadAnimation).toHaveBeenCalledTimes(1))

    unmount()

    expect(animation.destroy).toHaveBeenCalledTimes(1)
  })
})
