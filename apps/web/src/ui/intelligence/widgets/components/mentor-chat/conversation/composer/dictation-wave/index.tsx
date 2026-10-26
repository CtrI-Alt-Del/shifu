const BARS = ['first', 'second', 'third', 'fourth', 'fifth'] as const

export const DictationWave = () => (
  <span
    aria-hidden='true'
    className='dictation-wave flex h-4 items-center gap-0.5'
    data-testid='dictation-wave'
  >
    {BARS.map((bar) => (
      <span
        key={bar}
        className='dictation-wave__bar h-full w-0.5 rounded-full bg-primary'
      />
    ))}
  </span>
)
