/**
 * Token authentication utility.
 *
 * Flow:
 *  1. User visits https://<host>/<token>
 *  2. App extracts the token from the URL path
 *  3. Token is saved to localStorage
 *  4. URL is cleaned (redirect to /)
 *  5. All API calls include Authorization: Bearer <token>
 */

const STORAGE_KEY = 'workforce_twin_token'

export function getToken(): string | null {
  return localStorage.getItem(STORAGE_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(STORAGE_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(STORAGE_KEY)
}

/**
 * Check if the current URL path contains a token (first path segment
 * that doesn't match a known route). If found, save it and return true.
 */
const KNOWN_ROUTES = new Set(['', 'explorer', 'simulation', 'nova', 'deep-dive'])

export function extractTokenFromURL(): boolean {
  const path = window.location.pathname.replace(/^\/+/, '')
  const firstSegment = path.split('/')[0]

  if (firstSegment && !KNOWN_ROUTES.has(firstSegment)) {
    setToken(firstSegment)
    // Clean the URL — redirect to root
    window.history.replaceState({}, '', '/')
    return true
  }
  return false
}

export function isAuthenticated(): boolean {
  return getToken() !== null
}
