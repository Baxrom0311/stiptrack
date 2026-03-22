import { create } from "zustand"

import { clearAuthSession, getAccessToken } from "@/lib/auth-session"
import type { Role, User } from "@/types"

type AuthState = {
  user: User | null
  token: string | null
  role: Role | null
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: getAccessToken(),
  role: null,
  setUser: (user) => set({ user, role: user?.role ?? null }),
  setToken: (token) => {
    if (typeof window !== "undefined") {
      if (token) {
        localStorage.setItem("access_token", token)
      } else {
        localStorage.removeItem("access_token")
      }
    }
    if (!token) {
      clearAuthSession()
    }
    set({ token })
  },
  logout: () => {
    clearAuthSession()
    set({ user: null, token: null, role: null })
  },
}))
