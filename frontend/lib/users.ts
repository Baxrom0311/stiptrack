import api from "@/lib/api"
import type { Role, User } from "@/types"

type ListUsersParams = {
  role?: Role
  is_active?: boolean
  search?: string
  limit?: number
  offset?: number
}

export type UserAdminCreatePayload = {
  full_name: string
  email: string
  password: string
  role: Role
  department?: string | null
  student_id?: string | null
  is_supervisor: boolean
  is_active: boolean
}

export type UserAdminUpdatePayload = {
  full_name?: string
  email?: string
  password?: string
  role?: Role
  department?: string | null
  student_id?: string | null
  is_supervisor?: boolean
  is_active?: boolean
}

export async function listUsers(params: ListUsersParams = {}): Promise<User[]> {
  const { data } = await api.get<User[]>("/users", { params })
  return data
}

export async function createUser(payload: UserAdminCreatePayload): Promise<User> {
  const { data } = await api.post<User>("/users", payload)
  return data
}

export async function updateUser(userId: string, payload: UserAdminUpdatePayload): Promise<User> {
  const { data } = await api.patch<User>(`/users/${userId}`, payload)
  return data
}

export async function toggleUserActive(userId: string): Promise<User> {
  const { data } = await api.patch<User>(`/users/${userId}/toggle-active`)
  return data
}

export async function listSupervisors(): Promise<User[]> {
  const { data } = await api.get<User[]>("/users/supervisors")
  return data
}
