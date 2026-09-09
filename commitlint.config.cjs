module.exports = {
  extends: ['@commitlint/config-conventional'],
  plugins: [
    {
      rules: {
        'subject-ticket-pattern': (parsed) => {
          const subject = parsed.subject || ''

          const regex = /^[A-Z]+-\d+\s.+/

          if (regex.test(subject)) {
            return [true, '']
          }

          return [
            false,
            'O "subject" deve seguir o formato: TICKET-ID descrição (ex: SHIFU-138 add data parser)',
          ]
        },
      },
    },
  ],

  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore', 'ci', 'merge'],
    ],

    'subject-case': [0, 'always'],

    'subject-ticket-pattern': [2, 'always'],
  },
}
