import axios, { AxiosError, InternalAxiosRequestConfig } from "axios"

import {
  clearAuthSession,
  getAccessToken,
  getRefreshToken,
  persistAccessToken,
  persistRefreshToken,
} from "@/lib/auth-session"
import { useAuthStore } from "@/store/authStore"
import type { TokenPair } from "@/types"

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1").replace(/\/+$/, "")

const api = axios.create({
  baseURL: API_URL,
  timeout: 20000,
  headers: {
    Accept: "application/json",
  },
})

const refreshClient = axios.create({
  baseURL: API_URL,
  timeout: 20000,
  headers: {
    Accept: "application/json",
  },
})

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean
}

let refreshPromise: Promise<string> | null = null

function isAuthEndpoint(url?: string): boolean {
  return Boolean(
    url &&
      (url.includes("/auth/login") ||
        url.includes("/auth/register") ||
        url.includes("/auth/refresh") ||
        url.includes("/auth/logout")),
  )
}

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    throw new Error("Refresh token topilmadi.")
  }

  const { data } = await refreshClient.post<TokenPair>("/auth/refresh", {
    refresh_token: refreshToken,
  })

  persistAccessToken(data.access_token, data.access_expires_in)
  persistRefreshToken(data.refresh_token)
  useAuthStore.getState().setToken(data.access_token)

  return data.access_token
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (typeof window === "undefined") {
    return config
  }

  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined

    if (error.response?.status !== 401 || typeof window === "undefined" || !originalRequest) {
      return Promise.reject(error)
    }

    if (originalRequest._retry || isAuthEndpoint(originalRequest.url)) {
      useAuthStore.getState().logout()
      window.dispatchEvent(new Event("auth:unauthorized"))
      return Promise.reject(error)
    }

    if (!getRefreshToken()) {
      useAuthStore.getState().logout()
      window.dispatchEvent(new Event("auth:unauthorized"))
      return Promise.reject(error)
    }

    originalRequest._retry = true

    try {
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null
        })
      }

      const nextAccessToken = await refreshPromise
      originalRequest.headers = originalRequest.headers ?? {}
      originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`
      return api(originalRequest)
    } catch (refreshError) {
      clearAuthSession()
      useAuthStore.getState().logout()
      window.dispatchEvent(new Event("auth:unauthorized"))
      return Promise.reject(refreshError)
    }
  },
)

export default api
