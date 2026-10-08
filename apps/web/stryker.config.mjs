export default {
  testRunner: 'vitest',
  plugins: ['@stryker-mutator/vitest-runner'],
  vitest: { configFile: 'vitest.config.ts', related: true },
  coverageAnalysis: 'perTest',

  mutate: [
    'src/**/*.{ts,tsx}',
    '!src/**/tests/**',
    '!src/**/fakers/**',
    '!src/**/*.d.ts',
    '!src/routeTree.gen.ts',
  ],

  reporters: ['clear-text', 'progress', 'html', 'json'],
  htmlReporter: { fileName: 'reports/mutation/index.html' },
  jsonReporter: { fileName: 'reports/mutation/mutation.json' },
}
