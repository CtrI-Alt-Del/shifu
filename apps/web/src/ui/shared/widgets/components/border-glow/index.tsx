import type { PropsWithChildren } from 'react'

export type BorderGlowProps = PropsWithChildren<{
  className?: string
}>

// Adapted from React Bits Border Glow. See LICENSE.react-bits.md in this directory.
export const BorderGlow = ({ children, className = '' }: BorderGlowProps) => {
  return (
    <div className={`border-glow ${className}`}>
      <span aria-hidden='true' className='border-glow__mesh' />
      <span aria-hidden='true' className='border-glow__fill' />
      <span aria-hidden='true' className='border-glow__halo' />
      <div className='border-glow__content'>{children}</div>
    </div>
  )
}
