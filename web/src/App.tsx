import { Routes, Route, NavLink } from 'react-router-dom'
import { GeneratePage } from './pages/GeneratePage'
import { RunsPage } from './pages/RunsPage'
import { RunDetailPage } from './pages/RunDetailPage'

export function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>pptgen</h1>
        <p className="app-header__subtitle">Presentation Generator</p>
        <nav className="app-nav" aria-label="Main navigation">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'app-nav__link app-nav__link--active' : 'app-nav__link'}>
            Generate
          </NavLink>
          <NavLink to="/runs" className={({ isActive }) => isActive ? 'app-nav__link app-nav__link--active' : 'app-nav__link'}>
            Runs
          </NavLink>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<GeneratePage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
      </Routes>
    </div>
  )
}
