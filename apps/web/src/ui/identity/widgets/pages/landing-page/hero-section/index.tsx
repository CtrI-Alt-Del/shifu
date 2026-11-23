import { Anchor } from '@/ui/shared/widgets/components/anchor'

import { ProgressPreview } from './progress-preview'

export const HeroSection = () => {
  return (
    <section aria-labelledby='landing-hero-title' className='landing-page__hero'>
      <div className='landing-page__hero-copy'>
        <p className='landing-page__eyebrow'>Aprendizagem guiada, no seu ritmo</p>
        <h1 className='landing-page__title' id='landing-hero-title'>
          Veja sua evolução no que você quer aprender.
        </h1>
        <p className='landing-page__intro'>
          Entenda seu ponto de partida, pratique com orientação e acompanhe o que já
          aprendeu.
        </p>
        <div className='landing-page__hero-actions'>
          <Anchor className='landing-page__primary-action' route='register'>
            Criar conta
          </Anchor>
        </div>
        <p className='landing-page__hero-footnote'>
          Sem atalhos prontos. Com clareza sobre cada próximo passo.
        </p>
      </div>
      <ProgressPreview />
    </section>
  )
}
