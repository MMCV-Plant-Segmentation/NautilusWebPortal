import { AppBar, Box, Button, Toolbar, Typography } from '@mui/material'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth/useAuth'

export default function NavBar() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await api.logout()
    setUser(null)
    navigate('/login')
  }

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography
          variant="h6"
          component={Link}
          to="/"
          sx={{ flexGrow: 1, color: 'inherit', textDecoration: 'none' }}
        >
          NautilusWebPortal
        </Typography>
        {user && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2">{user.username}</Typography>
            {user.is_admin && (
              <Button color="inherit" component={Link} to="/admin">
                Admin panel
              </Button>
            )}
            <Button color="inherit" onClick={handleLogout}>
              Log out
            </Button>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  )
}
