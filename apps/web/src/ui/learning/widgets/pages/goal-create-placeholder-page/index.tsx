export const GoalCreatePlaceholderPage = () => {
  return (
    <div className='mx-auto flex min-h-[50vh] w-full max-w-7xl flex-col items-center justify-center gap-4 rounded-3xl border border-dashed border-border bg-card p-10 text-center'>
      <span className='inline-flex rounded-full border border-border bg-card px-3 py-1 text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground'>
        Em preparação
      </span>
      <h1 className='font-serif text-3xl tracking-tight sm:text-4xl'>
        A criação manual de Objetivos está sendo preparada.
      </h1>
      <p className='max-w-md text-sm leading-6 text-muted-foreground'>
        Em breve você poderá criar um Objetivo do zero, escolhendo suas próprias
        Habilidades.
      </p>
    </div>
  )
}
