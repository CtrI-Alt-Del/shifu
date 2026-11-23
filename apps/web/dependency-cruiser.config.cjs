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
    {
      name: 'recharts-only-in-chart-wrappers',
      comment:
        'Only the shared BarChart and LineChart wrappers may import recharts; feature widgets pass ChartDatum rows.',
      severity: 'error',
      from: { pathNot: '^src/ui/shared/widgets/components/(bar|line)-chart/' },
      to: { path: 'node_modules/recharts' },
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
