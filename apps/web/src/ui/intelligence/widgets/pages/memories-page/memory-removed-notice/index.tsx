import { Anchor } from '@/ui/shared/widgets/components/anchor'

export const MemoryRemovedNotice = () => (
  <section
    aria-label='Memória excluída'
    className='space-y-4 rounded-[10px] border border-border bg-card p-5'
  >
    <h2 className='font-serif text-2xl font-normal'>Memória excluída</h2>
    <p className='text-sm'>
      A memória foi removida. Mensagens, anexos e resumos antigos não voltarão a criá-la
      automaticamente.
    </p>
    <p className='text-sm text-muted-foreground'>
      Uma nova informação que você compartilhar pode gerar uma nova memória.
    </p>
    <Anchor
      className='inline-flex min-h-11 items-center rounded-md border border-control-border px-4 text-sm font-semibold text-foreground hover:bg-white/5'
      route='intelligence'
    >
      Voltar ao Mentor
    </Anchor>
  </section>
)
