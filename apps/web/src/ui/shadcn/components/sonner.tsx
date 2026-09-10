import { Toaster as Sonner, type ToasterProps } from 'sonner'

export function Toaster({ ...props }: ToasterProps) {
  return (
    <Sonner
      theme='dark'
      className='toaster group'
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:bg-surface group-[.toaster]:text-text-primary group-[.toaster]:border-divider group-[.toaster]:rounded-[2px]',
          description: 'group-[.toast]:text-text-muted',
          actionButton:
            'group-[.toast]:bg-selo-fill group-[.toast]:text-white group-[.toast]:rounded-[2px]',
          cancelButton:
            'group-[.toast]:bg-raised group-[.toast]:text-text-primary group-[.toast]:rounded-[2px]',
        },
      }}
      {...props}
    />
  )
}
