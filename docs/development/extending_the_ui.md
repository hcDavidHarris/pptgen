# Extending the Operator UI

This guide covers how to add new pages, components, and data hooks to the pptgen React frontend.

---

## Tech Stack

| Layer | Library |
|---|---|
| Framework | React 18 + TypeScript |
| Build | Vite |
| Routing | react-router-dom v6 |
| Testing | Vitest + @testing-library/react |
| Styles | Plain CSS (`app.css`) |

The frontend lives in `web/src/`. There is no CSS-in-JS or component library — all styles are in `web/src/app.css`.

---

## Adding a New Page

1. Create `web/src/pages/MyPage.tsx`:

```tsx
export function MyPage() {
  return (
    <main className="page-container">
      <div className="page-toolbar">
        <h2>My Page</h2>
      </div>
      {/* content */}
    </main>
  )
}
```

2. Register a route in `web/src/App.tsx`:

```tsx
import { MyPage } from './pages/MyPage'

// Inside <Routes>:
<Route path="/my-page" element={<MyPage />} />
```

3. Add a nav link in the `<nav>` inside `App.tsx`:

```tsx
<NavLink to="/my-page">My Page</NavLink>
```

4. Add tests in `web/src/__tests__/MyPage.test.tsx`. Wrap renders with `<MemoryRouter>`.

---

## Adding a New Data Hook

All data hooks follow the same `useReducer` + `useEffect` pattern. Example:

```tsx
// web/src/hooks/useMyData.ts
import { useReducer, useEffect } from 'react'

type State = { data: MyType | null; loading: boolean; error: Error | null }
type Action =
  | { type: 'loading' }
  | { type: 'success'; payload: MyType }
  | { type: 'error'; payload: Error }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'loading': return { data: null, loading: true, error: null }
    case 'success': return { data: action.payload, loading: false, error: null }
    case 'error':   return { data: null, loading: false, error: action.payload }
  }
}

export function useMyData(id: string) {
  const [state, dispatch] = useReducer(reducer, { data: null, loading: true, error: null })

  useEffect(() => {
    if (!id) return
    dispatch({ type: 'loading' })
    fetch(`/v1/my-resource/${id}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => dispatch({ type: 'success', payload: data }))
      .catch((err) => dispatch({ type: 'error', payload: err }))
  }, [id])

  return state
}
```

**Testing hooks via components:**

Don't test hooks directly. Render a component that uses the hook and stub `fetch` with `vi.stubGlobal('fetch', ...)`. Use the `makeFetchQueue` helper pattern from the existing test files for ordered responses.

---

## Adding a New Component

1. Create `web/src/components/MyComponent.tsx`
2. Add CSS classes to `web/src/app.css` — use BEM naming: `.my-component__element--modifier`
3. Add a test in `web/src/__tests__/MyComponent.test.tsx`

**CSS conventions:**

- `.page-container` — full-width page wrapper with max-width and padding (for non-grid pages)
- `.page-toolbar` — flex row with heading on left, actions on right
- `.btn .btn--primary / --secondary / --small` — buttons
- `.run-status-badge .run-status-badge--succeeded / --running / --failed / --cancelled` — status pills

---

## Testing Conventions

**Mock fetch with ordered responses:**

```tsx
function makeFetchQueue(...responses) {
  let index = 0
  return vi.fn().mockImplementation(() => {
    const r = responses[index] ?? responses[responses.length - 1]
    index++
    return Promise.resolve({ ok: r.ok, status: r.status, json: () => Promise.resolve(r.body) })
  })
}

// In test:
vi.stubGlobal('fetch', makeFetchQueue(ok(MY_DATA), ok(SECONDARY_DATA)))
```

**Hook call order matters.** If a page component uses three hooks that each call `fetch`, mock them in declaration order.

**Always wrap renders with `<MemoryRouter>`** when the component uses `NavLink`, `Link`, or `useNavigate`.

**Use `waitFor` for async rendering:**

```tsx
await waitFor(() => {
  expect(screen.getByText('some-value')).toBeInTheDocument()
})
```

---

## Types

All shared TypeScript types live in `web/src/types.ts`. API response shapes should be defined there. Use `api.ts` for fetch helper functions that call the backend.

---

## File Structure

```
web/src/
  App.tsx              — layout shell with nav and route definitions
  main.tsx             — entry point, wraps App in BrowserRouter
  app.css              — all styles
  types.ts             — shared TypeScript types
  api.ts               — fetch helpers
  utils/
    format.ts          — formatBytes, formatDuration, formatTime
  pages/
    GeneratePage.tsx
    RunsPage.tsx
    RunDetailPage.tsx
  components/
    RunTable.tsx
    RunStatusBadge.tsx
    RunSummaryCard.tsx
    RunMetricsCard.tsx
    ArtifactList.tsx
    ManifestViewer.tsx
    CopyButton.tsx
    EmptyState.tsx
    ErrorState.tsx
  hooks/
    useRuns.ts
    useRunDetail.ts
    useRunMetrics.ts
    useRunArtifacts.ts
  __tests__/
    App.test.tsx
    GeneratePage.test.tsx
    RunsPage.test.tsx
    RunDetailPage.test.tsx
    ArtifactList.test.tsx
    ManifestViewer.test.tsx
    RunStatusBadge.test.tsx
    RunSummaryCard.test.tsx
    RunTable.test.tsx
    utils/format.test.ts
```
