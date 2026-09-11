module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      from: {},
      to: { circular: true },
    },
    {
      name: 'core-does-not-depend-on-routes-or-ui',
      severity: 'error',
      from: { path: '^src/core/' },
      to: { path: '^src/(routes|ui)/' },
    },
    {
      name: 'rest-does-not-depend-on-ui',
      severity: 'error',
      from: { path: '^src/rest/' },
      to: { path: '^src/ui/' },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    enhancedResolveOptions: {
      exportsFields: ['exports'],
    },
    tsConfig: { fileName: 'tsconfig.json' },
  },
}
