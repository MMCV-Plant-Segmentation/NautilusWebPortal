import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Box, Button, Divider, Paper, TextField, Typography } from '@mui/material'
import { api, type User } from '../api'
import { useAuth } from '../auth/useAuth'

export default function LoginPage() {
  const { setUser } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [inviteCode, setInviteCode] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const res = await api.login(username, password)
    if (!res.ok) {
      const data = await res.json()
      setError(data.error)
      return
    }
    const meRes = await api.me()
    const user: User = await meRes.json()
    setUser(user)
    navigate('/')
  }

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault()
    const code = inviteCode.trim()
    if (code) navigate(`/invite/${encodeURIComponent(code)}`)
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8, px: 2 }}>
      <Paper sx={{ p: 4, width: '100%', maxWidth: 360 }}>
        <Typography variant="h5" gutterBottom>Log in</Typography>
        <Box component="form" onSubmit={handleLogin} noValidate>
          <TextField
            label="Username" fullWidth margin="normal" required autoFocus
            value={username} onChange={e => setUsername(e.target.value)}
          />
          <TextField
            label="Password" type="password" fullWidth margin="normal" required
            value={password} onChange={e => setPassword(e.target.value)}
          />
          {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
          <Button type="submit" variant="contained" fullWidth sx={{ mt: 2 }}>
            Log in
          </Button>
        </Box>

        <Divider sx={{ my: 3 }} />

        <Typography variant="subtitle2" gutterBottom>Have an invite code?</Typography>
        <Box component="form" onSubmit={handleInvite} sx={{ display: 'flex', gap: 1 }}>
          <TextField
            size="small" placeholder="Paste code here" sx={{ flex: 1 }}
            value={inviteCode} onChange={e => setInviteCode(e.target.value)}
          />
          <Button type="submit" variant="outlined">Go</Button>
        </Box>
      </Paper>
    </Box>
  )
}
