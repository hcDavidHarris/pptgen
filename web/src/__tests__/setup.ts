import '@testing-library/jest-dom'
import { vi } from 'vitest'

// jsdom does not implement navigator.clipboard.
// Install a controllable mock at setup time so component tests can assert on it.
const writeText = vi.fn().mockResolvedValue(undefined)

Object.defineProperty(navigator, 'clipboard', {
  value: { writeText },
  writable: true,
  configurable: true,
})

// Re-export for tests that need to assert on the mock directly.
export const clipboardWriteText = writeText
