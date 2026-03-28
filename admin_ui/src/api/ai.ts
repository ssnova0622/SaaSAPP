import { api } from './axios'

// ---- AI Config (tenant-level thresholds) ----
export type AIConfig = {
  no_show_reminder_threshold?: number
  no_show_high_risk_threshold?: number
  no_show_reminder_lead_hours?: number
  no_show_block_threshold?: number
  low_stock_days_default?: number
  low_stock_lead_time_days?: number
  low_stock_safety_days?: number
  low_stock_alert_days?: number
  cart_recovery_window_hours?: number
  cart_recovery_max_messages_per_cart?: number
  dynamic_pricing_min_multiplier?: number
  dynamic_pricing_max_multiplier?: number
  dynamic_pricing_max_discount_pct?: number
  slot_recs_prefer_morning?: boolean
  slot_recs_prefer_afternoon?: boolean
  features?: Record<string, boolean>
  whatsapp_intent_fallback_message?: string
}

export type AIConfigResponse = {
  tenant: string
  ai_config: AIConfig
  module_ai_caps?: Record<string, string[]>
}

export async function getAiConfig(tenant: string): Promise<AIConfigResponse> {
  const res = await api.get(`/tenants/${tenant}/ai/config`)
  return res.data as AIConfigResponse
}

export async function putAiConfig(tenant: string, ai_config: Partial<AIConfig>): Promise<AIConfigResponse> {
  const res = await api.put(`/tenants/${tenant}/ai/config`, { ai_config })
  return res.data as AIConfigResponse
}

export type LowStockItem = {
  sku: string
  name: string
  available_qty: number
  daily_demand: number
  days_to_stockout: number
  suggested_reorder_qty: number
}

export type ForecastResponse = {
  items: LowStockItem[]
  days: number
  lead_time: number
  safety_days: number
}

export async function getLowStockForecast(
  tenant: string,
  params: { days?: number; lead_time?: number; safety_days?: number; top?: number } = {}
): Promise<ForecastResponse> {
  const res = await api.get(`/tenants/${tenant}/ai/forecast_low_stock`, { params })
  return res.data as ForecastResponse
}

export async function postEvent(
  tenant: string,
  body: { type: string; ts?: number; data?: Record<string, any> }
): Promise<{ status: string; id: string }> {
  const res = await api.post(`/tenants/${tenant}/events`, body)
  return res.data as { status: string; id: string }
}

// ---- Predictions: Summary ----
export type PredictionsSummary = {
  tenant: string
  days: number
  generated_at: string
  low_stock_count: number
  predicted_oos_next_7d: number
  top_seller_skus: string[]
  abandoned_carts_24h: number
  anomaly_alerts: number
}

export async function getPredictionsSummary(tenant: string, params: { days?: number } = {}): Promise<PredictionsSummary> {
  const res = await api.get(`/tenants/${tenant}/ai/predictions/summary`, { params })
  return res.data as PredictionsSummary
}

// ---- Predictions: Top sellers ----
export type TopSellerItem = { sku: string; name: string; qty: number; revenue: number }
export type TopSellersResponse = { items: TopSellerItem[]; days: number }

export async function getTopSellers(tenant: string, params: { days?: number; top?: number } = {}): Promise<TopSellersResponse> {
  const res = await api.get(`/tenants/${tenant}/ai/top_sellers`, { params })
  return res.data as TopSellersResponse
}

// ---- Predictions: Sales forecast ----
export type SalesForecastPoint = { date: string; demand_units: number; revenue_estimate: number }
export type SalesForecastResponse = {
  items: SalesForecastPoint[]
  days: number
  horizon: number
  daily_demand: number
  avg_unit_price: number
}

export async function getSalesForecast(
  tenant: string,
  params: { days?: number; horizon?: number } = {}
): Promise<SalesForecastResponse> {
  const res = await api.get(`/tenants/${tenant}/ai/sales_forecast`, { params })
  return res.data as SalesForecastResponse
}

// ---- Predictions: Cart recovery ----
export type RecoverySku = { sku: string; name: string; qty: number }
export type CartRecoveryResponse = { window_hours: number; total_abandoned: number; top_skus: RecoverySku[] }

export async function getCartRecovery(
  tenant: string,
  params: { window_hours?: number; top?: number } = {}
): Promise<CartRecoveryResponse> {
  const res = await api.get(`/tenants/${tenant}/ai/cart_recovery`, { params })
  return res.data as CartRecoveryResponse
}

// ---- Appointment recommendations (clinic/salon) ----
export type RecommendSlotsResponse = {
  recommended: string[]
  rationale: string
  all_available: string[]
}

export async function getRecommendedSlots(
  tenant: string,
  params: { professional?: string; top?: number } = {}
): Promise<RecommendSlotsResponse> {
  const res = await api.get(`/tenants/${tenant}/ai/recommend_slots`, { params })
  return res.data as RecommendSlotsResponse
}
