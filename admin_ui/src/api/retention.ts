import { api } from './axios'

export type RetentionSummary = {
  tenant: string
  date: string
  active: number
  at_risk: number
  churned: number
}

export async function getRetentionSummary(tenant: string): Promise<RetentionSummary> {
  const res = await api.get(`/tenants/${tenant}/customers/retention/summary`)
  return res.data
}

export async function listRetention(
  tenant: string,
  params: { segment: 'active' | 'at_risk' | 'churned'; days?: number; page?: number; size?: number }
): Promise<{ items: any[]; total: number; page: number; size: number }> {
  const res = await api.get(`/tenants/${tenant}/customers/retention/list`, { params })
  return res.data
}
