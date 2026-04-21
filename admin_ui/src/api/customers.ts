import { api } from './axios'
import type { PhoneNumberJson } from '../utils/phone'

export type Customer = {
  tenant: string
  name: string
  /** May be omitted when API returns only `phone_number`. Use `displayE164FromEntity` / `formatEntityPhoneForDisplay`. */
  phone?: string
  phone_number?: PhoneNumberJson | null
  email?: string | null
  tags?: string[]
  active?: boolean
  created_by?: string | null
  updated_by?: string | null
}

export type CustomerList = {
  items: Customer[]
  total: number
  page: number
  size: number
}

export async function listCustomers(
  tenant: string,
  params: { search?: string; tag?: string; active?: boolean; page?: number; size?: number } = {}
): Promise<CustomerList> {
  const res = await api.get(`/tenants/${tenant}/customers`, { params })
  return res.data
}

export async function upsertCustomer(
  tenant: string,
  payload: { name?: string; phone: string; email?: string; tags?: string[]; active?: boolean }
) {
  const res = await api.post(`/tenants/${tenant}/customers`, payload)
  return res.data as Customer
}

export type CustomerImportResult = {
  inserted: number
  updated: number
  failed: number
  errors: Array<{ row: number; phone: string; error: string }>
}

export async function importCustomersCsv(tenant: string, file: File): Promise<CustomerImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post(`/tenants/${tenant}/customers/import`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
  return res.data as CustomerImportResult
}

export async function setCustomerActive(tenant: string, phone: string, active: boolean): Promise<Customer> {
  const res = await api.patch(`/tenants/${tenant}/customers/${encodeURIComponent(phone)}/status`, { active })
  return res.data as Customer
}
