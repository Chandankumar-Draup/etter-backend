import { Routes, Route, useLocation } from 'react-router-dom'
import Sidebar from './components/layout/Sidebar'
import Header from './components/layout/Header'
import { useTheme } from './hooks/useTheme'
import Dashboard from './pages/Dashboard'
import Explorer from './pages/Explorer'
import SimulationLab from './pages/SimulationLab'
import Nova from './pages/Nova'
import DeepDive from './pages/DeepDive'
import ErrorBoundary from './components/common/ErrorBoundary'

const PAGE_TITLES: Record<string, string> = {
  '/': 'Pulse',
  '/explorer': 'Current State Explorer',
  '/simulation': 'Simulation Lab',
  '/nova': 'Nova',
  '/deep-dive': 'Deep Dive',
}

export default function App() {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] ?? 'Workforce Twin'
  const { theme, toggle } = useTheme()

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header title={title} theme={theme} onToggleTheme={toggle} />
        <main className="flex-1 overflow-y-auto p-6 custom-scrollbar">
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/explorer" element={<Explorer />} />
              <Route path="/simulation" element={<SimulationLab />} />
              <Route path="/nova" element={<Nova />} />
              <Route path="/deep-dive" element={<DeepDive />} />
            </Routes>
          </ErrorBoundary>
        </main>
      </div>
    </div>
  )
}
