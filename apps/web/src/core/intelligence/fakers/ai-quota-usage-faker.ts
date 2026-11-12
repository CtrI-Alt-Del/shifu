import { faker } from '@faker-js/faker'

import type { AiQuotaStatus, AiQuotaUsage } from '@/core/intelligence/ai-quota-usage'

const PERCENTAGE_RANGES: Record<AiQuotaStatus, { min: number; max: number }> = {
  normal: { min: 0, max: 79 },
  near_limit: { min: 80, max: 99 },
  blocked: { min: 100, max: 130 },
}

export class AiQuotaUsageFaker {
  static fake(overrides: Partial<AiQuotaUsage> = {}): AiQuotaUsage {
    const status = overrides.status ?? 'normal'
    return {
      percentage: faker.number.int(PERCENTAGE_RANGES[status]),
      status,
      renewsOn: '2026-12-01',
      ...overrides,
    }
  }

  static fakeNearLimit(overrides: Partial<AiQuotaUsage> = {}): AiQuotaUsage {
    return AiQuotaUsageFaker.fake({ status: 'near_limit', ...overrides })
  }

  static fakeBlocked(overrides: Partial<AiQuotaUsage> = {}): AiQuotaUsage {
    return AiQuotaUsageFaker.fake({ status: 'blocked', ...overrides })
  }
}
