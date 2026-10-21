import { fileURLToPath, URL } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },

  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/tests/**',
        'src/**/*.{test,spec}.{ts,tsx}',
        'src/routeTree.gen.ts',
      ],
      reporter: ['text-summary', 'json', 'json-summary'],
      reportsDirectory: './coverage',
      reportOnFailure: true,
    },
    include: [
      'src/**/tests/**/*.{test,spec}.{ts,tsx}',
      'tests/unit/**/*.{test,spec}.{ts,tsx}',
    ],
  },
})
