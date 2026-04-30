import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Box, Button, Paper, TextField, Typography } from '@mui/material'
import { api } from '../api'

export default function InvitePage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [username, setUsername] = useState<string | null>(null)
  const [invalid, setInvalid] = useState(false)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api.invite
      .get(token)
      .then(res => (res.ok ? res.json() : Promise.reject()))
      .then(data => setUsername(data.username))
      .catch(() => setInvalid(true))
  }, [token])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) { setError('Passwords do not match'); return }
    const res = await api.invite.redeem(token!, password, confirm)
    const data = await res.json()
    if (!res.ok) { setError(data.error); return }
    navigate('/login')
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8, px: 2 }}>
      <Paper sx={{ p: 4, width: '100%', maxWidth: 400 }}>
        {invalid ? (
          <>
            <Typography variant="h5" gutterBottom>Link invalid or expired</Typography>
            <Typography>This invite link has expired or is no longer valid.</Typography>
            <Typography sx={{ mt: 1 }}>Please ask the admin to generate a new one.</Typography>
          </>
        ) : username !== null ? (
          <>
            <Typography variant="h5" gutterBottom>Hi, {username}!</Typography>
            <Typography gutterBottom>Set your password below.</Typography>
            <Box component="form" onSubmit={handleSubmit} noValidate>
              <TextField
                label="Password" type="password" fullWidth margin="normal" required
                slotProps={{ htmlInput: { minLength: 8 } }}
                value={password} onChange={e => setPassword(e.target.value)}
              />
              <TextField
                label="Confirm password" type="password" fullWidth margin="normal" required
                slotProps={{ htmlInput: { minLength: 8 } }}
                value={confirm} onChange={e => setConfirm(e.target.value)}
              />
              {error && <Alert severity="error" sx={{ mt: 1 }}>{error}</Alert>}
              <Button type="submit" variant="contained" fullWidth sx={{ mt: 2 }}>
                Set password
              </Button>
            </Box>
          </>
        ) : null}
      </Paper>
    </Box>
  )
}
