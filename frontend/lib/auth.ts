import api from "@/lib/api"
import type { TokenPair, User } from "@/types"

export type LoginPayload = {
  email: string
  password: string
}

export type RegisterPayload = {
  full_name: string
  email: string
  password: string
  department?: string | null
  student_id?: string | null
  is_supervisor?: boolean
}

export type UpdateMePayload = {
  full_name?: string
  department?: string | null
  student_id?: string | null
  is_supervisor?: boolean
}

type LogoutPayload = {
  refresh_token: string
}

type MessageResponse = {
  message: string
}

export async function login(payload: LoginPayload): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>("/auth/login", payload)
  return data
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post<User>("/auth/register", payload)
  return data
}

export async function logout(payload: LogoutPayload): Promise<MessageResponse> {
  const { data } = await api.post<MessageResponse>("/auth/logout", payload)
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me")
  return data
}

export async function updateMe(payload: UpdateMePayload): Promise<User> {
  const { data } = await api.patch<User>("/auth/me", payload)
  return data
}
