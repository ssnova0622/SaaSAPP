import { api } from './axios'

export type TenantService = {
  tenant: string
  name: string
  description?: string
  price: number
  duration: number
  active: boolean
  /** Booking window open time "HH:MM". When set, WhatsApp slots start from this time. */
  start_time?: string
  /** Booking window close time "HH:MM". When set, WhatsApp slots end at this time. */
  end_time?: string
}

export async function listServices(tenant: string, active?: boolean): Promise<TenantService[]> {
  const params: any = {}
  if (active !== undefined) params.active = active
  const res = await api.get(`/tenants/${tenant}/services`, { params })
  return res.data
}

export async function createService(tenant: string, service: Partial<TenantService>): Promise<TenantService> {
  const res = await api.post(`/tenants/${tenant}/services`, service)
  return res.data
}

export async function updateService(tenant: string, name: string, updates: Partial<TenantService>): Promise<TenantService> {
  const res = await api.patch(`/tenants/${tenant}/services/${encodeURIComponent(name)}`, updates)
  return res.data
}

export async function deleteService(tenant: string, name: string): Promise<{ ok: boolean }> {
  const res = await api.delete(`/tenants/${tenant}/services/${encodeURIComponent(name)}`)
  return res.data
}
