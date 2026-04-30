import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth/useAuth'
import NavBar from './components/NavBar'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import AdminPage from './pages/AdminPage'
import InvitePage from './pages/InvitePage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_admin) return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  const { user } = useAuth()
  return (
    <>
      {user && <NavBar />}
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<RequireAuth><HomePage /></RequireAuth>} />
        <Route path="/admin" element={<RequireAdmin><AdminPage /></RequireAdmin>} />
        <Route path="/invite/:token" element={<InvitePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
