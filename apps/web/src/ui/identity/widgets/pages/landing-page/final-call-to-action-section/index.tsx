import { Anchor } from '@/ui/shared/widgets/components/anchor'

export const FinalCallToActionSection = () => {
  return (
    <section aria-labelledby='landing-final-title' className='landing-final'>
      <div>
        <p className='landing-page__eyebrow'>O seu próximo passo começa aqui</p>
        <h2 id='landing-final-title'>Aprenda algo que importa para você.</h2>
      </div>
      <div className='landing-final__actions'>
        <Anchor className='landing-page__primary-action' route='register'>
          Criar conta
        </Anchor>
        <Anchor className='landing-final__privacy' route='privacy'>
          Leia nosso aviso de privacidade
        </Anchor>
      </div>
    </section>
  )
}
