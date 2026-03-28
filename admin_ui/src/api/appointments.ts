import { api } from './axios'

export type Appointment = {
  id: string
  tenant: string
  customer_name: string
  customer_phone: string
  professional: string
  time: string
  date?: string
  price: number
  status: 'booked' | 'canceled' | 'needs_reschedule' | 'blocked' | 'completed'
  created_by?: string
  updated_by?: string
}

export async function listAppointments(tenant: string, params: { professional?: string; date?: string; status?: string; search?: string; search_type?: string; search_value?: string } = {}): Promise<Appointment[]> {
  const res = await api.get(`/tenants/${tenant}/appointments`, { params })
  return res.data
}

export async function createAppointment(tenant: string, payload: { tenant: string; customer_name: string; customer_phone: string; professional: string; time: string; date?: string }) {
  const res = await api.post(`/tenants/${tenant}/appointments`, payload)
  return res.data as Appointment
}

export async function cancelAppointment(tenant: string, id: string, reason: 'canceled' | 'needs_reschedule' = 'canceled') {
  try {
    const res = await api.delete(`/tenants/${tenant}/appointments/${id}`, { params: { reason } })
    return res.data as Appointment
  } catch (err: any) {
    console.error('Failed to cancel appointment', err)
    throw err
  }
}

export async function rescheduleAppointment(tenant: string, id: string, payload: { new_time: string; new_date?: string }) {
  const res = await api.patch(`/tenants/${tenant}/appointments/${id}/reschedule`, payload)
  return res.data as Appointment
}

export async function updateAppointmentStatus(tenant: string, id: string, status: string) {
  const res = await api.patch(`/tenants/${tenant}/appointments/${id}/status`, { status })
  return res.data as Appointment
}

// ---- No-show blocked list (phones blocked from booking due to high no-show count) ----
export type NoShowBlockedItem = {
  phone: string
  name: string
  no_show_count: number
  updated_at?: string
}

export type NoShowBlockedResponse = {
  items: NoShowBlockedItem[]
  threshold: number
}

export async function listNoShowBlocked(tenant: string, search?: string): Promise<NoShowBlockedResponse> {
  const res = await api.get(`/tenants/${tenant}/no_show/blocked`, { params: search ? { search } : {} })
  return res.data as NoShowBlockedResponse
}

export async function resetNoShow(tenant: string, phone: string): Promise<{ ok: boolean; phone: string; name: string; no_show_count: number }> {
  const res = await api.post(`/tenants/${tenant}/no_show/reset`, { phone })
  return res.data
}
