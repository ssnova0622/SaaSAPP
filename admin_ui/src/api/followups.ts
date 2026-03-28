import { api } from './axios'

export type Followup = {
  id: string
  tenant: string
  appointment_id: string
  to_phone?: string | null
  to_email?: string | null
  type: string
  run_at: string
  status: 'scheduled' | 'sent' | 'failed' | 'canceled'
  payload?: {
    customer_name?: string
    professional?: string
    time?: string
    tenant?: string
  }
}

export async function listFollowups(
  tenant: string,
  params: { status?: string; customer_name?: string; customer_phone?: string; from_ts?: string; to_ts?: string; page?: number; size?: number } = {}
): Promise<{ items: Followup[]; total: number; page: number; size: number }> {
  const res = await api.get(`/tenants/${tenant}/followups`, { params })
  return res.data
}

export async function cancelFollowup(tenant: string, id: string) {
  const res = await api.post(`/tenants/${tenant}/followups/${id}/cancel`)
  return res.data as { status: string }
}
