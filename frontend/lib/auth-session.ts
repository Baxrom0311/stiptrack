import type { Role, TokenPair } from "@/types"

const ACCESS_TOKEN_KEY = "access_token"
const REFRESH_TOKEN_KEY = "refresh_token"

function setCookie(name: string, value: string, maxAgeSeconds: number) {
  if (typeof document === "undefined") {
    return
  }

  document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; Max-Age=${maxAgeSeconds}; SameSite=Lax`
}

function clearCookie(name: string) {
  if (typeof document === "undefined") {
    return
  }

  document.cookie = `${name}=; Path=/; Max-Age=0; SameSite=Lax`
}

export function persistAccessToken(token: string, accessExpiresIn: number) {
  if (typeof window === "undefined") {
    return
  }

  localStorage.setItem(ACCESS_TOKEN_KEY, token)
  setCookie(ACCESS_TOKEN_KEY, token, accessExpiresIn)
}

export function persistRefreshToken(token: string) {
  if (typeof window === "undefined") {
    return
  }

  localStorage.setItem(REFRESH_TOKEN_KEY, token)
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null
  }

  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") {
    return null
  }

  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function persistUserRole(role: Role, maxAgeSeconds = 60 * 60 * 24 * 7) {
  setCookie("role", role, maxAgeSeconds)
}

export function persistAuthSession(tokens: TokenPair, role: Role) {
  persistAccessToken(tokens.access_token, tokens.access_expires_in)
  persistRefreshToken(tokens.refresh_token)
  persistUserRole(role, Math.max(tokens.refresh_expires_in, 60 * 60))
}

export function clearAuthSession() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }

  clearCookie(ACCESS_TOKEN_KEY)
  clearCookie("role")
}
