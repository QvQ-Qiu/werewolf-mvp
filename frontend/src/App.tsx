import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { NotFoundPage } from './components/layout/PageState'
import LobbyPage from './pages/LobbyPage'
import GamePage from './pages/GamePage'
import ReplayPage from './pages/ReplayPage'
import PersonalityLibraryPage from './pages/PersonalityLibraryPage'
import StrategyLibraryPage from './pages/StrategyLibraryPage'

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<LobbyPage />} />
        <Route path="/libraries/personalities" element={<PersonalityLibraryPage />} />
        <Route path="/libraries/strategies" element={<StrategyLibraryPage />} />
        <Route path="/game/:gameId" element={<GamePage />} />
        <Route path="/replay/:gameId" element={<ReplayPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  )
}
