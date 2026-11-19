import type { CSSProperties } from 'react'
import { Toaster as SonnerToaster, type ToasterProps } from 'sonner'

export type { ToasterProps }

const THEME_VARIABLES = {
  '--normal-bg': 'var(--card)',
  '--normal-text': 'var(--foreground)',
  '--normal-border': 'var(--border)',
} as CSSProperties

export const Toaster = (props: ToasterProps) => (
  <SonnerToaster
    position='top-center'
    style={THEME_VARIABLES}
    theme='dark'
    visibleToasts={3}
    {...props}
  />
)
