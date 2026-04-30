import { Container, Typography } from '@mui/material'
import { useAuth } from '../auth/useAuth'

export default function HomePage() {
  const { user } = useAuth()
  return (
    <Container sx={{ mt: 4 }}>
      <Typography variant="h5">Welcome, {user?.username}!</Typography>
      <Typography color="text.secondary" sx={{ mt: 1 }}>
        The job submission interface is coming soon.
      </Typography>
    </Container>
  )
}
