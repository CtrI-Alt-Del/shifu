import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ModulePageHeader } from '@/ui/shared/widgets/components/module-page-header'

const guidance = [
  {
    description:
      'Converse sobre uma dúvida e receba ajuda conectada ao seu contexto de aprendizagem.',
    title: 'Mentor',
  },
  {
    description:
      'Saia de uma intenção ampla para um objetivo possível, com próximos passos claros.',
    title: 'Planejador de objetivos',
  },
] as const

export const IntelligencePage = () => {
  return (
    <div className='space-y-10'>
      <ModulePageHeader
        description='Apoio para transformar intenção em caminho, preservando suas escolhas e seu ritmo.'
        eyebrow='Módulo inteligência'
        title='Mais clareza para continuar.'
      />

      <section className='rounded-3xl border border-border bg-card p-7 shadow-card sm:p-9'>
        <div className='max-w-2xl'>
          <span className='inline-flex rounded-full bg-accent px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-primary'>
            Apoio contextual
          </span>
          <h2 className='mt-5 font-serif text-3xl font-bold tracking-tight sm:text-4xl'>
            Você traz a intenção. A Inteligência ajuda a dar forma.
          </h2>
          <p className='mt-4 leading-7 text-muted-foreground'>
            Use este espaço para refletir, planejar e encontrar uma próxima ação que
            combine com o momento.
          </p>
        </div>
        <div className='mt-8 grid gap-4 md:grid-cols-2'>
          {guidance.map((item) => (
            <article className='rounded-2xl bg-muted p-6' key={item.title}>
              <span className='grid size-11 place-items-center rounded-xl bg-card text-xl text-primary'>
                <Icon name='sparkles' />
              </span>
              <h3 className='mt-5 font-serif text-2xl font-bold'>{item.title}</h3>
              <p className='mt-2 text-sm leading-6 text-muted-foreground'>
                {item.description}
              </p>
              <span className='mt-6 inline-flex rounded-full border border-border bg-card px-3 py-1 text-xs font-bold uppercase tracking-[0.1em] text-muted-foreground'>
                Em preparação
              </span>
            </article>
          ))}
        </div>
      </section>

      <section className='flex flex-col gap-5 rounded-2xl border border-dashed border-primary/40 bg-accent/50 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-7'>
        <div>
          <p className='font-serif text-xl font-bold'>
            Enquanto isso, continue construindo seu repertório.
          </p>
          <p className='mt-1 text-sm text-muted-foreground'>
            O aprendizado é o ponto de partida para uma orientação cada vez mais útil.
          </p>
        </div>
        <Anchor
          className='inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-bold text-primary-foreground transition-colors hover:bg-primary/90'
          route='learning'
        >
          Ir para aprendizado <Icon name='arrow-right' />
        </Anchor>
      </section>
    </div>
  )
}
