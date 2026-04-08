import { api } from './axios'

/** Single tenant row for Super Admin tenant tracker (GET /admin/tenants/overview). */
export type TenantOverviewRow = {
  tenant: string
  plan?: string | null
  trial_ends_at?: string | null
  active: boolean
  payment_config?: { provider?: string; currency?: string }
  whatsapp_inbound_count: number
  whatsapp_outbound_count: number
  revenue_30d?: number
  owner_email?: string | null
  owner_phone?: string | null
  category?: string
}

export type TenantsOverviewResponse = {
  tenants: TenantOverviewRow[]
}

/** Super Admin only. List all tenants with plan, payment, WhatsApp count, trial, status, revenue. */
export async function getTenantsOverview(): Promise<TenantOverviewRow[]> {
  const res = await api.get<TenantsOverviewResponse>('/admin/tenants/overview')
  return res.data?.tenants ?? []
}
