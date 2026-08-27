import { afterAll, beforeAll, describe, expect, test } from 'vitest'

import { formatLocalDate, getPresetDateRange } from './reportDates'

describe('report preset local calendar dates', () => {
  const originalTimezone = process.env.TZ

  beforeAll(() => { process.env.TZ = 'Asia/Manila' })
  afterAll(() => { process.env.TZ = originalTimezone })

  test('does not fall back to the previous UTC day just after midnight in UTC+8', () => {
    const nearMidnight = new Date('2026-08-26T16:30:00.000Z')

    expect(nearMidnight.toISOString().slice(0, 10)).toBe('2026-08-26')
    expect(formatLocalDate(nearMidnight)).toBe('2026-08-27')
    expect(getPresetDateRange('today', nearMidnight)).toEqual(['2026-08-27', '2026-08-27'])
  })

  test('calculates every preset from the local day', () => {
    const nearMidnight = new Date('2026-08-26T16:30:00.000Z')

    expect(getPresetDateRange('7', nearMidnight)).toEqual(['2026-08-21', '2026-08-27'])
    expect(getPresetDateRange('30', nearMidnight)).toEqual(['2026-07-29', '2026-08-27'])
    expect(getPresetDateRange('month', nearMidnight)).toEqual(['2026-08-01', '2026-08-27'])
  })
})
