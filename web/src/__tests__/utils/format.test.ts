import { describe, it, expect } from 'vitest'
import { formatBytes, formatDuration, formatTime } from '../../utils/format'

describe('formatBytes', () => {
  it('formats bytes under 1 KiB', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(1023)).toBe('1023 B')
  })

  it('formats KiB range', () => {
    expect(formatBytes(1024)).toBe('1.0 KiB')
    expect(formatBytes(2048)).toBe('2.0 KiB')
    expect(formatBytes(1536)).toBe('1.5 KiB')
  })

  it('formats MiB range', () => {
    expect(formatBytes(1024 * 1024)).toBe('1.0 MiB')
    expect(formatBytes(1024 * 1024 * 2.5)).toBe('2.5 MiB')
  })
})

describe('formatDuration', () => {
  it('returns em dash for null', () => {
    expect(formatDuration(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatDuration(undefined)).toBe('—')
  })

  it('formats milliseconds under 1 second', () => {
    expect(formatDuration(0)).toBe('0 ms')
    expect(formatDuration(500)).toBe('500 ms')
    expect(formatDuration(999)).toBe('999 ms')
  })

  it('formats seconds at 1 second boundary', () => {
    expect(formatDuration(1000)).toBe('1.0 s')
  })

  it('formats seconds for larger values', () => {
    expect(formatDuration(2500)).toBe('2.5 s')
    expect(formatDuration(60000)).toBe('60.0 s')
  })
})

describe('formatTime', () => {
  it('returns em dash for null', () => {
    expect(formatTime(null)).toBe('—')
  })

  it('returns em dash for undefined', () => {
    expect(formatTime(undefined)).toBe('—')
  })

  it('returns em dash for empty string', () => {
    expect(formatTime('')).toBe('—')
  })

  it('returns formatted date string for valid ISO input', () => {
    const result = formatTime('2026-03-24T10:00:00.000Z')
    // Should be a non-empty string — locale-dependent so just check it is truthy and not an em dash
    expect(result).toBeTruthy()
    expect(result).not.toBe('—')
  })

  it('returns the original string for non-parseable input', () => {
    expect(formatTime('not-a-date')).toBe('not-a-date')
  })
})
