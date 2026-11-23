import { Anchor } from '@/ui/shared/widgets/components/anchor'

import { FinalCallToActionSection } from './final-call-to-action-section'
import { HeroSection } from './hero-section'
import { LearningJourneySection } from './learning-journey-section'
import { LearningTopicsSection } from './learning-topics-section'
import { MentorSection } from './mentor-section'
import { useLandingPage } from './use-landing-page'

import './landing-page.css'

export const LandingPage = () => {
  const { isDocumentVisible } = useLandingPage()

  return (
    <div className='landing-page' data-motion-enabled={isDocumentVisible}>
      <div aria-hidden='true' className='landing-page__ambient' />
      <header className='landing-page__header'>
        <Anchor aria-label='Shifu — início' className='landing-page__brand' route='root'>
          <span>Shifu</span>
          <span aria-hidden='true' className='landing-page__brand-mark'>
            師
          </span>
        </Anchor>
        <nav aria-label='Acesso à conta' className='landing-page__header-actions'>
          <Anchor className='landing-page__sign-in' route='login'>
            Entrar
          </Anchor>
          <Anchor className='landing-page__header-register' route='register'>
            Criar conta
          </Anchor>
        </nav>
      </header>

      <main>
        <HeroSection />
        <LearningJourneySection />
        <LearningTopicsSection />
        <MentorSection />
        <FinalCallToActionSection />
      </main>

      <footer className='landing-page__footer'>
        <Anchor
          aria-label='Shifu — início'
          className='landing-page__footer-brand'
          route='root'
        >
          Shifu <span aria-hidden='true'>師</span>
        </Anchor>
        <p>Aprender leva tempo. Cada passo conta.</p>
        <Anchor className='landing-page__privacy-link' route='privacy'>
          Aviso de privacidade
        </Anchor>
      </footer>
    </div>
  )
}
