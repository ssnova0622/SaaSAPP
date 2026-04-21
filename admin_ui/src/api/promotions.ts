import { api } from './axios'

export type Attachment = {
  type: 'image' | 'video' | 'link' | 'document'
  url: string
  name?: string
}

export type Button = {
  id: string
  title: string
  url?: string
}

export type ListRow = {
  id: string
  title: string
  description?: string
  url?: string
}

export type ListSection = {
  title?: string
  rows: ListRow[]
}

export type CtaEntry = {
  id?: string | null
  display_text: string
  url: string
}

/** All supported promotion delivery channels. */
export type PromotionChannel =
  | 'whatsapp'
  | 'email'
  | 'both'
  | 'sms'
  | 'sms+email'
  | 'sms+whatsapp'
  | 'all'

export type Promotion = {
  id: string
  tenant: string
  name: string
  channel: PromotionChannel
  message: string
  html_message?: string | null
  media_url?: string | null
  attachments?: Attachment[] | null
  interactive_type?: 'button' | 'list' | 'cta_url' | null
  buttons?: Button[] | null
  list_sections?: ListSection[] | null
  cta_url?: string | null
  cta_display_text?: string | null
  cta_footer?: string | null
  cta_entries?: CtaEntry[] | null
  cta_append_urls_to_body?: boolean | null
  offer_code?: string | null
  audience: any
  status: string
  schedule_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  created_by?: string | null
  updated_by?: string | null
  stats?: { total?: number; sent?: number; failed?: number } | null
  /** Present when this promotion was created by resending another (completed) promotion */
  resend_of?: string | null
}

export async function listPromotions(tenant: string): Promise<Promotion[]> {
  const res = await api.get(`/tenants/${tenant}/promotions`)
  return res.data
}

export async function createPromotion(tenant: string, payload: Partial<Promotion>) {
  const res = await api.post(`/tenants/${tenant}/promotions`, payload)
  return res.data as Promotion
}

export async function getPromotion(tenant: string, id: string) {
  const res = await api.get(`/tenants/${tenant}/promotions/${id}`)
  return res.data as Promotion
}

export async function updatePromotion(tenant: string, id: string, payload: Partial<Promotion>) {
  const res = await api.put(`/tenants/${tenant}/promotions/${id}`, payload)
  return res.data as Promotion
}

export async function deletePromotion(tenant: string, id: string): Promise<void> {
  await api.delete(`/tenants/${tenant}/promotions/${id}`)
}

export async function sendPromotion(
  tenant: string,
  id: string,
  body?: { resend?: boolean; audience?: Record<string, unknown> },
) {
  const res = await api.post(`/tenants/${tenant}/promotions/${id}/send`, body ?? {})
  return res.data as {
    id: string
    tenant: string
    status: string
    total: number
    sent: number
    failed: number
    source_promotion_id?: string | null
  }
}

export async function getPromotionLogs(
  tenant: string,
  id: string,
  params: { page?: number; size?: number; status?: string; channel?: string; from_ts?: string; to_ts?: string } = {}
) {
  const res = await api.get(`/tenants/${tenant}/promotions/${id}/logs`, { params })
  return res.data as { items: any[]; total: number; page: number; size: number }
}
