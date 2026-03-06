/**
 * Token authentication utility.
 *
 * Prod/QA flow:
 *  1. User is redirected from etter.draup.com with token in URL: https://<host>/<token>
 *  2. App extracts token from URL path, saves to localStorage, cleans URL
 *  3. App calls POST /auth/check_auth with Bearer token to validate & get user info
 *  4. User info (company_name, company_id, etc.) stored in localStorage
 *  5. All workforce twin API calls include Authorization: Bearer <token>
 *
 * Local dev flow:
 *  No token in URL → app works without auth (backend must be running without auth
 *  or with a test token set manually via setToken())
 */

const TOKEN_KEY = 'workforce_twin_token'
const USER_KEY = 'workforce_twin_user'

// ─── Token ───

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

// ─── User info (from check_auth) ───

export interface UserInfo {
  email: string
  company_name: string
  company_id: number
  first_name: string
  last_name: string
  username: string
  group: string
}

export function getUser(): UserInfo | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}

function setUser(user: UserInfo): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

// ─── Token extraction from URL ───

const KNOWN_ROUTES = new Set(['', 'explorer', 'simulation', 'nova', 'deep-dive'])

export function extractTokenFromURL(): boolean {
  const path = window.location.pathname.replace(/^\/+/, '')
  const firstSegment = path.split('/')[0]

  if (firstSegment && !KNOWN_ROUTES.has(firstSegment)) {
    setToken(firstSegment)
    window.history.replaceState({}, '', '/')
    return true
  }
  return false
}

// ─── Validate token via check_auth ───

/**
 * Call the etter backend's check_auth endpoint to validate the token
 * and retrieve user/company info.
 *
 * AUTH_BASE_URL is the etter backend root (e.g. https://api.draup.com/api).
 * In local dev, this goes through the Vite proxy.
 */
export async function validateToken(): Promise<UserInfo | null> {
  const token = getToken()
  if (!token) return null

  // Already validated in this session
  const cached = getUser()
  if (cached) return cached

  const authBase = (window as any).__ETTER_API_BASE__ || '/etter-api'

  try {
    const res = await fetch(`${authBase}/auth/check_auth`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    })

    if (!res.ok) {
      clearToken()
      return null
    }

    const body = await res.json()
    if (body.status !== 'Success' || !body.data) {
      clearToken()
      return null
    }

    const user: UserInfo = body.data
    setUser(user)
    return user
  } catch {
    // Network error — don't clear token, might be a transient failure
    return null
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null
}
