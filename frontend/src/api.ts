let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

async function apiFetch(input: RequestInfo, init?: RequestInit): Promise<Response> {
  const res = await fetch(input, { credentials: 'include', ...init })
  if (res.status === 401) onUnauthorized?.()
  return res
}

export type User = { id: number; username: string; is_admin: boolean }
export type UserRecord = {
  id: number
  username: string
  has_password: boolean
  invite: { token: string; expires: number } | null
}

export const api = {
  me: () => fetch('/api/me', { credentials: 'include' }),

  login: (username: string, password: string) =>
    apiFetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }),

  logout: () => apiFetch('/api/logout', { method: 'POST' }),

  users: {
    list: () => apiFetch('/api/users'),
    create: (username: string) =>
      apiFetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username }),
      }),
    reset: (id: number) => apiFetch(`/api/users/${id}/reset`, { method: 'POST' }),
    delete: (id: number) => apiFetch(`/api/users/${id}`, { method: 'DELETE' }),
  },

  invite: {
    get: (token: string) => fetch(`/api/invite/${token}`, { credentials: 'include' }),
    redeem: (token: string, password: string, confirm: string) =>
      apiFetch(`/api/invite/${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password, confirm }),
      }),
  },
}
