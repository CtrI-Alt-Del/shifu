import { createFileRoute } from '@tanstack/react-router'

import { PrivacyPolicyPage } from '@/ui/identity/widgets/pages/privacy-policy-page'

export const Route = createFileRoute('/privacy/')({
  head: () => ({
    meta: [
      { title: 'Política de privacidade — Shifu' },
      {
        name: 'description',
        content:
          'Conheça os dados tratados pelo Shifu, suas finalidades, os direitos dos titulares e como falar com a Encarregada.',
      },
    ],
  }),
  component: PrivacyPolicyPage,
})
