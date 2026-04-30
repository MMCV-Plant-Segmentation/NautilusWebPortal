import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Paper,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import ContentCopyIcon from '@mui/icons-material/ContentCopy'
import { api, type UserRecord } from '../api'

function timeRemaining(expires: number): string {
  const secs = expires - Date.now() / 1000
  if (secs <= 0) return 'expired'
  const days = Math.floor(secs / 86400)
  const hours = Math.floor((secs % 86400) / 3600)
  if (days > 0) return `${days}d ${hours}h`
  return `${hours}h ${Math.floor((secs % 3600) / 60)}m`
}

type Snack = { msg: string; severity: 'success' | 'error' }

export default function AdminPage() {
  const [users, setUsers] = useState<UserRecord[]>([])
  const [newUsername, setNewUsername] = useState('')
  const [snack, setSnack] = useState<Snack | null>(null)

  const toast = (msg: string, severity: 'success' | 'error') => setSnack({ msg, severity })

  const loadUsers = useCallback(async () => {
    const res = await api.users.list()
    if (res.ok) setUsers(await res.json())
  }, [])

  useEffect(() => { loadUsers() }, [loadUsers])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    const username = newUsername.trim()
    if (!username) return
    const res = await api.users.create(username)
    const data = await res.json()
    if (!res.ok) { toast(data.error, 'error'); return }
    setNewUsername('')
    toast(`User "${username}" created.`, 'success')
    loadUsers()
  }

  const handleReset = async (id: number) => {
    const res = await api.users.reset(id)
    const data = await res.json()
    if (!res.ok) { toast(data.error, 'error'); return }
    toast('Re-invite sent — new invite link generated.', 'success')
    loadUsers()
  }

  const handleDelete = async (id: number, username: string) => {
    if (!confirm(`Delete user "${username}"? This cannot be undone.`)) return
    const res = await api.users.delete(id)
    const data = await res.json()
    if (!res.ok) { toast(data.error, 'error'); return }
    toast(`User "${username}" deleted.`, 'success')
    loadUsers()
  }

  const copy = (text: string, label: string) => {
    navigator.clipboard?.writeText(text).catch(() => {})
    toast(`${label} copied!`, 'success')
  }

  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom>Admin panel</Typography>

      <Box component="form" onSubmit={handleCreate} sx={{ display: 'flex', gap: 1, mb: 3 }}>
        <TextField
          label="New user" size="small" required
          value={newUsername} onChange={e => setNewUsername(e.target.value)}
        />
        <Button type="submit" variant="contained">Create</Button>
      </Box>

      <Paper>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Username</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {users.map(u => (
              <TableRow key={u.id}>
                <TableCell>{u.username}</TableCell>
                <TableCell>
                  {u.has_password ? (
                    <Chip label="Active" color="success" size="small" />
                  ) : u.invite ? (
                    <Box>
                      <Typography variant="body2" gutterBottom>
                        Invite pending — expires in {timeRemaining(u.invite.expires)}
                      </Typography>
                      <Typography variant="caption" sx={{ fontFamily: 'monospace', display: 'block', mb: 1 }}>
                        {u.invite.token}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button size="small" variant="outlined" startIcon={<ContentCopyIcon />}
                          onClick={() => copy(u.invite!.token, 'Invite code')}>
                          Copy code
                        </Button>
                        <Tooltip title="The invite link includes this page's hostname — make sure you're accessing the portal from the right host before sharing.">
                          <Button size="small" variant="outlined" startIcon={<ContentCopyIcon />}
                            onClick={() => copy(`${window.location.origin}/invite/${u.invite!.token}`, 'Invite link')}>
                            Copy link
                          </Button>
                        </Tooltip>
                      </Box>
                    </Box>
                  ) : (
                    <Chip label="No invite" size="small" />
                  )}
                </TableCell>
                <TableCell>
                  {u.username !== 'admin' && (
                    <Box>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Button size="small" variant="outlined" onClick={() => handleReset(u.id)}>
                          Re-invite
                        </Button>
                        <Button size="small" variant="outlined" color="error" onClick={() => handleDelete(u.id, u.username)}>
                          Delete
                        </Button>
                      </Box>
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                        Re-invite revokes the current password (if there is one) and generates a new invite link.
                      </Typography>
                    </Box>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Snackbar
        open={!!snack}
        autoHideDuration={5000}
        onClose={() => setSnack(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={snack?.severity} onClose={() => setSnack(null)}>
          {snack?.msg}
        </Alert>
      </Snackbar>
    </Container>
  )
}
