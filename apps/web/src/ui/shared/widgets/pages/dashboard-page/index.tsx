import { Anchor } from '@/ui/shared/widgets/components/anchor'

export const DashboardPage = () => {
  return (
    <div className='space-y-10'>
      <section className='rounded-3xl border border-border bg-card p-7 sm:p-9'>
        <p className='text-sm font-semibold text-primary'>Objetivos</p>
        <h1 className='mt-4 max-w-2xl font-serif text-4xl leading-tight tracking-tight sm:text-5xl'>
          Dê forma ao que você quer aprender.
        </h1>
        <p className='mt-4 max-w-xl leading-7 text-muted-foreground'>
          Organize sua jornada em objetivos claros e encontre o próximo passo para
          continuar avançando.
        </p>
        <Anchor
          className='mt-7 inline-flex min-h-11 items-center justify-center rounded-md bg-primary px-5 font-semibold text-primary-foreground transition-colors hover:bg-primary/90'
          route='learning'
        >
          Explorar aprendizado
        </Anchor>
      </section>

      <section>
        <p className='text-sm font-semibold text-primary'>Sua jornada</p>
        <h2 className='mt-2 font-serif text-2xl tracking-tight'>
          Objetivos em andamento
        </h2>
        <div className='mt-5 rounded-2xl border border-dashed border-border bg-card p-7'>
          <p className='font-serif text-xl'>Seu primeiro objetivo começa aqui.</p>
          <p className='mt-2 max-w-xl text-sm leading-6 text-muted-foreground'>
            Quando você criar um objetivo, suas habilidades e próximos passos aparecerão
            neste espaço.
          </p>
        </div>
      </section>
    </div>
  )
}
