import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ModulePageHeader } from '@/ui/shared/widgets/components/module-page-header'

const skills = [
  {
    description: 'Quebre problemas em partes menores e encontre caminhos.',
    level: 'Comece aqui',
    title: 'Pensamento lógico',
  },
  {
    description: 'Dê nomes e organize as informações que um programa usa.',
    level: 'Fundamentos',
    title: 'Variáveis e tipos',
  },
  {
    description: 'Crie regras para que seu código tome decisões.',
    level: 'Fundamentos',
    title: 'Condicionais',
  },
  {
    description: 'Repita ações com clareza e controle.',
    level: 'Próximo passo',
    title: 'Repetição',
  },
] as const

export const CurriculumPage = () => {
  return (
    <div className='mx-auto w-full max-w-7xl space-y-10'>
      <ModulePageHeader
        description='Um mapa de habilidades e competências para você entender o que estudar e por quê.'
        eyebrow='Módulo currículo'
        title='Aprenda com um caminho claro.'
      />

      <section className='rounded-3xl border border-border bg-card p-7 shadow-card sm:p-9'>
        <div className='grid gap-8 lg:grid-cols-[1.3fr_1fr] lg:items-end'>
          <div>
            <span className='inline-flex rounded-full bg-accent px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-primary'>
              Trilha inicial
            </span>
            <h2 className='mt-5 max-w-xl font-serif text-3xl font-bold tracking-tight sm:text-4xl'>
              Fundamentos de programação
            </h2>
            <p className='mt-4 max-w-xl leading-7 text-muted-foreground'>
              Uma sequência para construir repertório, praticar conceitos essenciais e
              ganhar autonomia.
            </p>
          </div>
          <div className='grid grid-cols-3 gap-3 text-center'>
            {[
              ['12', 'habilidades'],
              ['36', 'competências'],
              ['3', 'etapas'],
            ].map(([value, label]) => (
              <div className='rounded-2xl bg-muted p-4' key={label}>
                <p className='font-serif text-2xl font-bold text-primary'>{value}</p>
                <p className='mt-1 text-xs font-semibold text-muted-foreground'>
                  {label}
                </p>
              </div>
            ))}
          </div>
        </div>
        <Anchor
          className='mt-8 inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-5 font-bold text-primary-foreground transition-colors hover:bg-primary/90'
          route='learning'
        >
          Começar a aprender <Icon name='arrow-right' />
        </Anchor>
      </section>

      <section>
        <p className='text-sm font-bold uppercase tracking-[0.14em] text-primary'>
          Mapa de habilidades
        </p>
        <h2 className='mt-2 font-serif text-2xl font-bold'>O que você pode explorar</h2>
        <div className='mt-5 grid gap-4 sm:grid-cols-2'>
          {skills.map((skill, index) => (
            <article
              className='rounded-2xl border border-border bg-card p-6 shadow-card'
              key={skill.title}
            >
              <div className='flex items-start justify-between gap-4'>
                <span className='grid size-10 place-items-center rounded-xl bg-muted font-bold text-primary'>
                  0{index + 1}
                </span>
                <span className='rounded-full bg-muted px-3 py-1 text-xs font-bold text-muted-foreground'>
                  {skill.level}
                </span>
              </div>
              <h3 className='mt-6 font-serif text-xl font-bold'>{skill.title}</h3>
              <p className='mt-2 text-sm leading-6 text-muted-foreground'>
                {skill.description}
              </p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
