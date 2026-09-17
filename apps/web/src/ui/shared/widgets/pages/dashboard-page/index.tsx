import { Anchor } from '@/ui/shared/widgets/components/anchor'
import { ModulePageHeader } from '@/ui/shared/widgets/components/module-page-header'

export const DashboardPage = () => {
  return (
    <div className='space-y-10'>
      <ModulePageHeader
        description='Escolha onde continuar e mantenha sua jornada de aprendizagem em movimento.'
        eyebrow='Espaço do aprendiz'
        title='Bem-vindo ao Shifu'
      />

      <section className='rounded-3xl border border-border bg-card p-7 shadow-card sm:p-9'>
        <p className='text-sm font-bold uppercase tracking-[0.14em] text-primary'>
          Próximo passo
        </p>
        <h2 className='mt-2 font-serif text-3xl font-bold'>
          Continue aprendendo no seu ritmo
        </h2>
        <p className='mt-3 max-w-2xl leading-7 text-muted-foreground'>
          Retome suas atividades, acompanhe suas conquistas ou converse com o Mentor
          quando precisar de orientação.
        </p>
        <div className='mt-6 flex flex-wrap gap-3'>
          <Anchor
            className='inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-5 font-bold text-primary-foreground transition-colors hover:bg-primary/90'
            route='learning'
          >
            Ir para aprendizagem
          </Anchor>
          <Anchor
            className='inline-flex min-h-11 items-center justify-center rounded-xl border border-border px-5 font-bold text-foreground transition-colors hover:bg-muted'
            route='intelligence'
          >
            Abrir Mentor
          </Anchor>
        </div>
      </section>
    </div>
  )
}
