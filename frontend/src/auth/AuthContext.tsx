import React, { createContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { type User, setUnauthorizedHandler } from '../api'

type AuthContextType = {
  user: User | null
  loading: boolean
  setUser: (user: User | null) => void
}

export const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  setUser: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const logout = useCallback(() => {
    setUser(null)
    navigate('/login', { replace: true })
  }, [navigate])

  useEffect(() => {
    // Use plain fetch for the initial check — the global 401 handler isn't set yet,
    // and a 401 here just means "not logged in", not "session expired mid-use".
    fetch('/api/me', { credentials: 'include' })
      .then(res => (res.ok ? res.json() : null))
      .then(data => {
        setUser(data)
        setLoading(false)
        setUnauthorizedHandler(logout)
      })
      .catch(() => {
        setLoading(false)
        setUnauthorizedHandler(logout)
      })
  }, [logout])

  return (
    <AuthContext.Provider value={{ user, loading, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}
