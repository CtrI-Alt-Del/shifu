import type { Variants } from 'motion/react'

const EASE_OUT = [0.16, 1, 0.3, 1] as const

// Entrance choreography shared by the app's pages. Parents only stagger
// their children; under `MotionConfig reducedMotion='user'` the offsets and
// scales are dropped, and `MotionEntrance` skips the entrance entirely.
export const ENTRANCE_STAGGER: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.1, delayChildren: 0.05 } },
}

// Long collections (calendar days, XP records) cascade quickly so the last
// item still lands well under a second after its container.
export const ENTRANCE_FAST_STAGGER: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.02 } },
}

export const ENTRANCE_SECTION: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    // Children start while the section is still settling, so deep trees
    // (families of cards with progress fills) finish close together.
    transition: {
      duration: 0.55,
      ease: EASE_OUT,
      delayChildren: 0.15,
      staggerChildren: 0.06,
    },
  },
}

export const ENTRANCE_CARD: Variants = {
  hidden: { opacity: 0, y: 14, scale: 0.97 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.45, ease: EASE_OUT, delayChildren: 0.1 },
  },
}

export const ENTRANCE_POP: Variants = {
  hidden: { opacity: 0, scale: 0.6 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { type: 'spring', stiffness: 420, damping: 22 },
  },
}

export const ENTRANCE_ROW: Variants = {
  hidden: { opacity: 0, x: -16 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.45, ease: EASE_OUT } },
}

export const ENTRANCE_MEDAL: Variants = {
  hidden: { scale: 0.4, rotate: -20 },
  visible: {
    scale: 1,
    rotate: 0,
    transition: { type: 'spring', stiffness: 380, damping: 16 },
  },
}

// Progress fills grow once their card has entered; pass the final percentage
// through the `custom` prop.
export const ENTRANCE_FILL: Variants = {
  hidden: { width: '0%' },
  visible: (percentage: number) => ({
    width: `${percentage}%`,
    transition: { duration: 0.8, delay: 0.2, ease: EASE_OUT },
  }),
}

// Side panels slide in from their edge before their content cascades.
export const ENTRANCE_SLIDE: Variants = {
  hidden: { opacity: 0, x: -24 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.55,
      ease: EASE_OUT,
      delayChildren: 0.15,
      staggerChildren: 0.05,
    },
  },
}

// Plain children (headings, copy) rise into place.
export const ENTRANCE_RISE: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT } },
}

// Chat cascades start from the newest message, which sits at the bottom of
// the scrolled view, and work upwards.
export const ENTRANCE_MESSAGE_LIST: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.05, staggerDirection: -1 } },
}

// Message cards arrive from their speaker's side: pass `1` for the learner
// (right) and `-1` for the Mentor (left) through the `custom` prop.
export const ENTRANCE_MESSAGE: Variants = {
  hidden: (direction: number) => ({ opacity: 0, x: direction * 28, y: 6, scale: 0.97 }),
  visible: {
    opacity: 1,
    x: 0,
    y: 0,
    scale: 1,
    transition: { type: 'spring', stiffness: 320, damping: 28 },
  },
}
