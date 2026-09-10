import type { ReactNode } from 'react'

export type ModulePageHeaderProps = {
  action?: ReactNode
  description: string
  eyebrow: string
  title: string
}

export const ModulePageHeader = ({
  action,
  description,
  eyebrow,
  title,
}: ModulePageHeaderProps) => {
  return (
    <header className='flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between'>
      <div className='max-w-2xl'>
        <p className='text-xs font-bold uppercase tracking-[0.16em] text-primary'>
          {eyebrow}
        </p>
        <h1 className='mt-3 font-serif text-4xl font-bold tracking-tight text-foreground sm:text-5xl'>
          {title}
        </h1>
        <p className='mt-3 text-base leading-7 text-muted-foreground sm:text-lg'>
          {description}
        </p>
      </div>
      {action}
    </header>
  )
}
