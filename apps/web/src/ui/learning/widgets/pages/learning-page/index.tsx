import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { Icon } from '@/ui/shared/widgets/components/icon'
import { ModulePageHeader } from '@/ui/shared/widgets/components/module-page-header'
import { ProgressMeter } from '@/ui/shared/widgets/components/progress-meter'

export const LearningPage = () => {
  return (
    <div className='mx-auto w-full max-w-7xl space-y-10'>
      <ModulePageHeader
        action={
          <Anchor
            className='inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-bold text-primary-foreground transition-colors hover:bg-primary/90'
            route='curriculum'
          >
            Ver currículo <Icon name='arrow-right' />
          </Anchor>
        }
        description='Transforme seus objetivos em prática e acompanhe o que está fazendo sentido para você.'
        eyebrow='Módulo aprendizado'
        title='Seu próximo passo começa aqui.'
      />

      <section className='rounded-3xl border border-border bg-card p-7 shadow-card sm:p-9'>
        <div className='flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between'>
          <div className='max-w-2xl'>
            <span className='inline-flex rounded-full bg-accent px-3 py-1 text-xs font-bold uppercase tracking-[0.12em] text-primary'>
              Objetivo em andamento
            </span>
            <h2 className='mt-5 font-serif text-3xl font-bold tracking-tight'>
              Fundamentos de programação
            </h2>
            <p className='mt-3 leading-7 text-muted-foreground'>
              Construa uma base para resolver problemas e criar seus primeiros programas.
            </p>
          </div>
          <div className='w-full max-w-xs'>
            <ProgressMeter label='Progresso do objetivo' value={42} />
          </div>
        </div>
        <div className='mt-8 flex flex-col gap-4 rounded-2xl bg-muted p-5 sm:flex-row sm:items-center sm:justify-between'>
          <div>
            <p className='text-xs font-bold uppercase tracking-[0.12em] text-primary'>
              Próxima atividade
            </p>
            <p className='mt-1 font-serif text-xl font-bold'>Pensamento lógico</p>
            <p className='mt-1 text-sm text-muted-foreground'>Prática guiada · 10 min</p>
          </div>
          <Anchor
            className='inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-5 font-bold text-primary-foreground transition-colors hover:bg-primary/90'
            route='curriculum'
          >
            Explorar habilidade
          </Anchor>
        </div>
      </section>

      <section>
        <div className='flex items-end justify-between gap-4'>
          <div>
            <p className='text-sm font-bold uppercase tracking-[0.14em] text-primary'>
              Painel de aprendizagem
            </p>
            <h2 className='mt-2 font-serif text-2xl font-bold'>Acompanhe sua jornada</h2>
          </div>
          <span className='hidden text-sm font-semibold text-muted-foreground sm:inline'>
            Atualizado agora
          </span>
        </div>
        <div className='mt-5 grid gap-4 md:grid-cols-3'>
          {[
            ['Diagnóstico', 'Descubra seu ponto de partida', 'Disponível'],
            ['Foco atual', 'Pensamento lógico', 'Em prática'],
            ['Histórico', 'Veja suas tentativas e aprendizados', 'Em breve'],
          ].map(([title, description, status]) => (
            <article
              className='rounded-2xl border border-border bg-card p-6 shadow-card'
              key={title}
            >
              <div className='flex items-center justify-between gap-3'>
                <h3 className='font-serif text-xl font-bold'>{title}</h3>
                <span className='size-2 rounded-full bg-success' />
              </div>
              <p className='mt-3 text-sm leading-6 text-muted-foreground'>
                {description}
              </p>
              <p className='mt-6 text-xs font-bold uppercase tracking-[0.12em] text-primary'>
                {status}
              </p>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
