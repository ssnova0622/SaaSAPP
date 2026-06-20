import { api } from './axios'
import type { AxiosError } from 'axios'

export type User = {
  id?: string
  email: string
  role: 'super_admin' | 'tenant_admin' | 'staff' | 'admin'
  tenant?: string | null
  display_name?: string
  caps?: string[]
  status?: 'active' | 'disabled'
  created_at?: string
  updated_at?: string
}

export type UsersList = { items: User[]; total: number; page: number; size: number }

export async function listUsers(params: { tenant?: string; search?: string; role?: string; page?: number; size?: number } = {}) {
  const res = await api.get<UsersList>('/users', { params })
  return res.data
}

export async function createUser(payload: { email: string; password: string; role: User['role']; tenant?: string; display_name?: string; caps?: string[] }) {
  const res = await api.post<User>('/users', payload)
  return res.data
}

export async function getUser(id: string) {
  const res = await api.get<User>(`/users/${encodeURIComponent(id)}`)
  return res.data
}

export async function updateUser(id: string, patch: Partial<User> & { password?: string; caps?: string[] }) {
  const res = await api.patch<User>(`/users/${encodeURIComponent(id)}`, patch)
  return res.data
}

export async function setPassword(id: string, password: string) {
  const res = await api.patch<User>(`/users/${encodeURIComponent(id)}/password`, { password })
  return res.data
}

export type PermissionProfile = {
  id: string
  label: string
  description: string
  caps: string[]
}

export type AssignableCap = {
  id: string
  label: string
  description: string
  group: string
  module: string
}

export type PermissionProfilesResponse = {
  profiles: PermissionProfile[]
  assignable_caps: AssignableCap[]
}

export async function getPermissionProfiles(tenant?: string): Promise<PermissionProfilesResponse> {
  const res = await api.get<PermissionProfilesResponse>('/meta/permission-profiles', {
    params: tenant ? { tenant } : undefined,
  })
  return res.data
}

export async function updateUserCaps(id: string, caps: string[]): Promise<User> {
  const res = await api.patch<User>(`/users/${encodeURIComponent(id)}`, { caps })
  return res.data
}

// Suppress unused import warning (AxiosError used in consumers via re-export)
export type { AxiosError }
