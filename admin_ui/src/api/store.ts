import { api } from './axios'

// ===== Types =====
export type CartItem = { sku: string; qty: number; price_snapshot: number; unit?: string; name?: string; manual?: boolean }
export type Cart = {
  tenant?: string
  customer_phone: string
  items: CartItem[]
  totals: { subtotal: number }
  status?: string
}

export type CheckoutPayload = {
  fulfillment_mode: 'delivery' | 'pickup'
  address?: { label?: string; line1: string; line2?: string; area?: string; city: string; pincode: string }
  payment_method: 'ONLINE' | 'COD'
  /** Optional cart-level discount (percent or amount off subtotal) */
  discount_info?: { type: 'percent' | 'amount'; value: number; code?: string }
}

export type CheckoutResult = { order_id: string; payment_url?: string; intent_id?: string }

export type OrderItem = {
  sku: string
  qty: number
  price_snapshot: number
  price?: number
  unit?: string
  name?: string
  manual?: boolean
  offer_applied?: boolean
  price_before_offer?: number
}
export type PaymentInfo = { method: 'ONLINE' | 'COD'; status: 'pending' | 'paid' | 'failed'; provider?: string; intent_id?: string; paid_at?: string }
export type Order = {
  id: string
  tenant?: string
  customer: { phone: string; name?: string }
  address?: { label?: string; line1?: string; line2?: string; area?: string; city?: string; pincode?: string }
  fulfillment_mode: 'delivery' | 'pickup'
  items: OrderItem[]
  totals: { subtotal: number; discount?: number; grand_total?: number }
  /** Cart-level discount applied by store owner (saved with order for audit) */
  discount_info?: { type: 'percent' | 'amount'; value: number; code?: string }
  status: 'placed' | 'confirmed' | 'picking' | 'ready_for_pickup' | 'out_for_delivery' | 'delivered' | 'canceled'
  payment: PaymentInfo
  notes?: string
  timeline?: Array<{ ts: string; event: string; meta?: any }>
  created_at?: string
  updated_at?: string
}

export type OrderList = { items: Order[]; total: number; page: number; size: number }

// ===== API =====
export async function getCart(tenant: string, phone: string): Promise<Cart> {
  const res = await api.get(`/tenants/${tenant}/carts/${encodeURIComponent(phone)}`)
  return res.data as Cart
}

export async function putCart(tenant: string, phone: string, items: CartItem[]): Promise<Cart> {
  const res = await api.put(`/tenants/${tenant}/carts/${encodeURIComponent(phone)}`, { items })
  return res.data as Cart
}

export async function checkout(tenant: string, phone: string, payload: CheckoutPayload): Promise<CheckoutResult> {
  const res = await api.post(`/tenants/${tenant}/carts/${encodeURIComponent(phone)}/checkout`, payload)
  return res.data as CheckoutResult
}

export async function listOrders(
  tenant: string,
  params: { status?: string; search?: string; page?: number; size?: number } = {}
): Promise<OrderList> {
  const res = await api.get(`/tenants/${tenant}/orders`, { params })
  return res.data as OrderList
}

export async function getOrder(tenant: string, orderId: string): Promise<Order> {
  const res = await api.get(`/tenants/${tenant}/orders/${encodeURIComponent(orderId)}`)
  return res.data as Order
}

export async function updateOrderStatus(tenant: string, orderId: string, status: Order['status']): Promise<Order> {
  const res = await api.patch(`/tenants/${tenant}/orders/${encodeURIComponent(orderId)}/status`, { status })
  return res.data as Order
}

/** Send order summary to customer via tenant's WhatsApp. */
export async function sendOrderWhatsApp(tenant: string, orderId: string): Promise<{ ok: boolean; message?: string }> {
  const res = await api.post(`/tenants/${tenant}/orders/${encodeURIComponent(orderId)}/send-whatsapp`)
  return res.data as { ok: boolean; message?: string }
}

// Edit order items (before delivery). Optional notes stored on order for tracking (e.g. offer applied).
export async function updateOrderItems(
  tenant: string,
  orderId: string,
  payload: {
    items: Array<{ sku: string; qty: number; price_snapshot: number; name?: string; offer_applied?: boolean; price_before_offer?: number }>
    notes?: string
  }
): Promise<Order> {
  const res = await api.patch(`/tenants/${tenant}/orders/${encodeURIComponent(orderId)}/items`, payload)
  return res.data as Order
}
