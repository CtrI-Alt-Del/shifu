import { useSquareBackground } from './use-square-background'

export const SquareBackground = () => {
  const { backgroundRef, squareCount } = useSquareBackground()

  return (
    <div
      aria-hidden='true'
      className='square-background pointer-events-none fixed inset-0 z-0 overflow-hidden'
      ref={backgroundRef}
    >
      <div className='square-background__wash' />
      <div className='square-background__grid'>
        {Array.from({ length: squareCount }, (_, index) => (
          <span
            className='square-background__cell'
            data-square-background-cell
            key={`square-${index + 1}`}
          />
        ))}
      </div>
    </div>
  )
}
