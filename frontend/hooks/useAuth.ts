"use client"

import { useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"

import {
  getMe as fetchMe,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  type LoginPayload,
  type RegisterPayload,
} from "@/lib/auth"
import {
  clearAuthSession,
  getRefreshToken,
  persistAccessToken,
  persistAuthSession,
  persistUserRole,
} from "@/lib/auth-session"
import { useAuthStore } from "@/store/authStore"
import type { TokenPair, User } from "@/types"

type LoginResult = {
  tokens: TokenPair
  user: User
}

export function useAuth() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const token = useAuthStore((state) => state.token)
  const role = useAuthStore((state) => state.role)
  const setUser = useAuthStore((state) => state.setUser)
  const setToken = useAuthStore((state) => state.setToken)
  const clearStore = useAuthStore((state) => state.logout)

  const me = useCallback(async (): Promise<User> => {
    const currentUser = await fetchMe()
    persistUserRole(currentUser.role)
    setUser(currentUser)
    return currentUser
  }, [setUser])

  const login = useCallback(
    async (payload: LoginPayload): Promise<LoginResult> => {
      const tokens = await loginRequest(payload)
      persistAccessToken(tokens.access_token, tokens.access_expires_in)

      try {
        const currentUser = await fetchMe()
        persistAuthSession(tokens, currentUser.role)
        setUser(currentUser)
        setToken(tokens.access_token)
        return { tokens, user: currentUser }
      } catch (error) {
        clearStore()
        clearAuthSession()
        throw error
      }
    },
    [clearStore, setToken, setUser],
  )

  const register = useCallback((payload: RegisterPayload) => registerRequest(payload), [])

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken()

    try {
      if (refreshToken) {
        await logoutRequest({ refresh_token: refreshToken })
      }
    } finally {
      clearStore()
      queryClient.clear()
    }
  }, [clearStore, queryClient])

  return {
    user,
    token,
    role,
    isAuthenticated: Boolean(token),
    login,
    register,
    logout,
    me,
  }
}
