import { api } from './axios'
// Lightweight in-memory cache for tenant settings to reduce duplicate fetches across quick navigations
const __tenantSettingsCache: Map<string, TenantSettings> = new Map()

export type TenantBasic = {
  tenant: string
  category?: string
  /** Shown at top of page instead of tenant id when set */
  display_name?: string | null
  owner_email?: string | null
  owner_phone?: string | null
  tz?: string | null
  date_format?: 'DD-MM-YYYY' | 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD'
  invoice_delivery?: string | null
  active?: boolean
}

export async function listTenants(): Promise<TenantBasic[]> {
  const res = await api.get<TenantBasic[]>('/tenants')
  return res.data
}

/** Which channels the tenant can use for notifications (promotions, follow-ups, etc.) */
export type MessagingChannels = {
  email?: boolean
  whatsapp?: boolean
  sms?: boolean
}

export type SmsConfig = {
  enabled?: boolean
  provider?: string
  from_number?: string
  account_sid?: string
  auth_token?: string
}

export type TenantSettings = TenantBasic & {
  /** Business address (e.g. for booking confirmation messages) */
  address?: string
  /** Map link (e.g. Google Maps URL) for location in messages */
  location?: string
  /** Subscription plan: basic | pro | enterprise */
  plan?: string
  /** Which channels are enabled for this tenant */
  messaging_channels?: MessagingChannels
  /** SMS provider config when SMS channel is enabled */
  sms_config?: SmsConfig
  followup_prefs?: any
  templates?: any
  store_enabled?: boolean
  modules?: string[]
  capabilities?: string[]
  ai?: {
    low_stock?: boolean
    catalog_assist?: boolean
    recommendations?: boolean
    predictions_enabled?: boolean
  }
  payment_config?: {
    provider?: 'dummy' | 'stripe' | 'razorpay'
    currency?: string
    methods?: Array<'ONLINE' | 'COD'>
    test_mode?: boolean
    webhook_secret?: string
  }
  delivery_config?: {
    delivery_enabled?: boolean
    pickup_enabled?: boolean
    service_areas?: string[]
    store_hours?: string[]
  }
  whatsapp_config?: Record<string, any>
}

/** Plan definition for Super Admin (tenant creation and settings) */
export type PlanInfo = {
  id: string
  label: string
  description: string
  modules: string[]
  capabilities: string[]
}

export async function listPlans(): Promise<PlanInfo[]> {
  const res = await api.get<{ plans: PlanInfo[] }>('/plans')
  return res.data.plans || []
}

export async function getTenantSettings(tenant: string): Promise<TenantSettings> {
  // Read-through cache
  if (__tenantSettingsCache.has(tenant)) {
    return __tenantSettingsCache.get(tenant) as TenantSettings
  }
  const res = await api.get<TenantSettings>(`/tenants/${tenant}`)
  const data = res.data
  try { __tenantSettingsCache.set(tenant, data) } catch { /* ignore */ }
  return data
}

export async function updateTenantSettings(tenant: string, payload: Partial<TenantSettings>): Promise<TenantSettings> {
  const res = await api.put<TenantSettings>(`/tenants/${tenant}`, payload)
  const data = res.data
  try { __tenantSettingsCache.set(tenant, data) } catch { /* ignore */ }
  return data
}

// --- WhatsApp Config (per tenant) ---
// (WhatsApp Config types and APIs are defined later in this file to include both Twilio and Meta Cloud fields.)

// --- Create Tenant ---
export type TenantCreate = {
  tenant: string
  category?: string
  /** Subscription plan: basic | pro | enterprise. Defaults to pro. */
  plan?: string
  admin_email?: string
  admin_password?: string
  admin_display_name?: string
  professionals?: Array<{
    name: string
    price?: number
    slots?: Array<string | { time: string; status?: string }>
  }>
}

// ---- WhatsApp config types/APIs ----
export type WhatsAppConfig = {
  provider: 'twilio' | 'meta_cloud'
  from_numbers: string[]
  from_number?: string // legacy (read-only)
  webhook_secret?: string
  account_sid?: string
  auth_token?: string
  locale_default?: string
  // Meta Cloud specific (dummy-friendly)
  phone_number_id?: string
  access_token?: string
  // App-specific defaults
  active_menu_id?: string
}

export async function getWhatsAppConfig(tenant: string): Promise<WhatsAppConfig>{
  const res = await api.get(`/tenants/${encodeURIComponent(tenant)}/whatsapp/config`)
  return res.data
}

export async function putWhatsAppConfig(tenant: string, cfg: WhatsAppConfig): Promise<WhatsAppConfig>{
  const res = await api.put(`/tenants/${encodeURIComponent(tenant)}/whatsapp/config`, cfg)
  return res.data
}

export type MessageCategorySection = {
  id: string
  title: string
  keys: string[]
}

/** Default messages from ``default_message`` + tenant merge (Messages admin screen). */
export type WhatsAppTemplateBundle = {
  keys: string[]
  /** Grouped keys (e.g. wa_* → WhatsApp). */
  categories: MessageCategorySection[]
  /** Row titles from ``default_message.labels``. */
  labels: Record<string, string>
  /** Platform default bodies (``default_message.templates``). */
  defaults: Record<string, string>
  /** Effective text for this tenant (defaults + ``tenant_message_templates``). */
  templates: Record<string, string>
  /** True when tenant has an explicit key in ``tenant_message_templates``. */
  customized: Record<string, boolean>
}

export async function getWhatsAppTemplateBundle(tenant: string): Promise<WhatsAppTemplateBundle> {
  const res = await api.get<WhatsAppTemplateBundle>(
    `/tenants/${encodeURIComponent(tenant)}/message-templates/whatsapp-bundle`,
  )
  return res.data
}

export async function putTenantMessageTemplates(
  tenant: string,
  templates: Record<string, string>,
): Promise<{ templates: Record<string, string> }> {
  const res = await api.put<{ templates: Record<string, string> }>(
    `/tenants/${encodeURIComponent(tenant)}/message-templates`,
    { templates },
  )
  return res.data
}

/** Super Admin: update platform ``default_message`` (all tenants unless overridden). */
export async function putDefaultMessagesAdmin(body: {
  templates?: Record<string, string>
  labels?: Record<string, string>
}): Promise<{ templates: Record<string, string>; labels: Record<string, string> }> {
  const res = await api.put(`/admin/default-messages`, body)
  return res.data
}

export type TenantCreateResponse = {
  tenant: string
  category: string
  professionals: Array<{ name: string; price: number; slots: Array<{ time: string; status: string }> }>
  appointments: number
  revenue: number
}

export async function createTenant(payload: TenantCreate): Promise<TenantCreateResponse> {
  const res = await api.post<TenantCreateResponse>('/tenants', payload)
  return res.data
}

export async function deleteTenant(tenant: string): Promise<void> {
  await api.delete(`/tenants/${encodeURIComponent(tenant)}`)
}

// --- Activate/Deactivate Tenant ---
export async function setTenantActive(tenant: string, active: boolean): Promise<TenantSettings> {
  const res = await api.patch<TenantSettings>(`/tenants/${encodeURIComponent(tenant)}/status`, { active })
  const data = res.data
  try { __tenantSettingsCache.set(tenant, data) } catch { /* ignore */ }
  return data
}

// Helper to clear tenant settings cache, e.g., on logout
export function clearTenantSettingsCache() {
  try { __tenantSettingsCache.clear() } catch { /* ignore */ }
}
