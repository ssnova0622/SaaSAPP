import { api } from './axios'
import type { PhoneNumberJson } from '../utils/phone'

export type Staff = {
  tenant: string
  id: string
  name: string
  role: string
  phone?: string | null
  phone_number?: PhoneNumberJson | null
  email?: string | null
  skills: string[]
  active: boolean
  created_at?: string
  updated_at?: string
  created_by?: string
  updated_by?: string
}

export type StaffList = {
  items: Staff[]
  total: number
  page: number
  size: number
}

export type StaffCreate = {
  name: string
  role: string
  phone?: string
  email?: string
  skills?: string[]
  active?: boolean
}

export type StaffUpdate = Partial<StaffCreate>

export async function listStaff(
  tenant: string,
  params: { search?: string; role?: string; active?: boolean; page?: number; size?: number } = {}
): Promise<StaffList> {
  const res = await api.get(`/tenants/${tenant}/staff`, { params })
  return res.data
}

export async function createStaff(tenant: string, payload: StaffCreate): Promise<Staff> {
  const res = await api.post(`/tenants/${tenant}/staff`, payload)
  return res.data
}

export async function getStaff(tenant: string, id: string): Promise<Staff> {
  const res = await api.get(`/tenants/${tenant}/staff/${id}`)
  return res.data
}

export async function updateStaff(tenant: string, id: string, payload: StaffUpdate): Promise<Staff> {
  const res = await api.put(`/tenants/${tenant}/staff/${id}`, payload)
  return res.data
}

export async function deleteStaff(tenant: string, id: string): Promise<void> {
  await api.delete(`/tenants/${tenant}/staff/${id}`)
}

export type StaffImportResult = {
  inserted: number
  updated: number
  failed: number
  errors: Array<{ row: number; name: string; error: string }>
}

export async function importStaffCsv(tenant: string, file: File): Promise<StaffImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post(`/tenants/${tenant}/staff/import`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data as StaffImportResult
}
