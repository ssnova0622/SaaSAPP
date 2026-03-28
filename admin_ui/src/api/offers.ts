import { api } from './axios'

export type Offer = {
  id: string
  title: string
  description: string
  valid_from: string
  valid_until: string
  product_skus?: string[]
  discount_info?: Record<string, unknown>
  brochure_url?: string
  active: boolean
  created_at?: string
  updated_at?: string
  created_by?: string
}

/** List active offers (no auth). For public catalog to show was/now pricing. */
export async function listActiveOffersPublic(tenant: string): Promise<{ items: Offer[]; total: number }> {
  const res = await api.get<{ items: Offer[]; total: number }>(`/tenants/${tenant}/offers/active`)
  return res.data
}

export type OfferCreatePayload = {
  title: string
  description?: string
  valid_from?: string
  valid_until?: string
  product_skus?: string[]
  discount_info?: Record<string, unknown>
  brochure_url?: string
  active?: boolean
}

export type ListOffersResponse = {
  items: Offer[]
  total: number
  page: number
  size: number
}

export async function listOffers(
  tenant: string,
  params?: { active_only?: boolean; page?: number; size?: number }
): Promise<ListOffersResponse> {
  const res = await api.get<ListOffersResponse>(`/tenants/${tenant}/offers`, { params: params || {} })
  return res.data
}

export async function createOffer(tenant: string, payload: OfferCreatePayload): Promise<Offer> {
  const res = await api.post<Offer>(`/tenants/${tenant}/offers`, payload)
  return res.data
}

export async function getOffer(tenant: string, offerId: string): Promise<Offer> {
  const res = await api.get<Offer>(`/tenants/${tenant}/offers/${encodeURIComponent(offerId)}`)
  return res.data
}

export async function updateOffer(
  tenant: string,
  offerId: string,
  payload: Partial<OfferCreatePayload>
): Promise<Offer> {
  const res = await api.patch<Offer>(`/tenants/${tenant}/offers/${encodeURIComponent(offerId)}`, payload)
  return res.data
}

export async function deleteOffer(tenant: string, offerId: string): Promise<{ ok: boolean }> {
  const res = await api.delete<{ ok: boolean }>(`/tenants/${tenant}/offers/${encodeURIComponent(offerId)}`)
  return res.data
}

/** Bulk create offers (e.g. from uploaded brochure/CSV/Excel). */
export async function bulkCreateOffers(
  tenant: string,
  offers: OfferCreatePayload[]
): Promise<{ created: number; items: Offer[]; errors?: string[] }> {
  const res = await api.post<{ created: number; items: Offer[]; errors?: string[] }>(
    `/tenants/${tenant}/offers/bulk`,
    { offers }
  )
  return res.data
}
