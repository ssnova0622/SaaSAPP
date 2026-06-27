import { api } from './axios'

export type WhatsAppMenu = {
  tenant: string
  menu_id: string
  name: string
  status: 'draft' | 'published'
  version?: number
  tree?: any
  locales?: Record<string, any>
  updated_at?: string
  updated_by?: string
  published_at?: string
  published_by?: string
}

export async function listMenus(tenant: string): Promise<{ items: WhatsAppMenu[]; total: number }>{
  const res = await api.get(`/tenants/${encodeURIComponent(tenant)}/whatsapp/menus`)
  return res.data
}

export async function getMenu(
  tenant: string,
  menuId: string,
  status?: 'draft' | 'published',
  version?: number,
): Promise<WhatsAppMenu>{
  const url = `/tenants/${encodeURIComponent(tenant)}/whatsapp/menus/${encodeURIComponent(menuId)}`
  const params: any = {}
  if (status) params.status = status
  if (typeof version === 'number') params.version = version
  const res = await api.get(url, { params: Object.keys(params).length ? params : undefined })
  return res.data
}

export async function upsertMenu(tenant: string, payload: { menu_id: string; name: string; tree: any; locales?: any }): Promise<WhatsAppMenu>{
  const res = await api.post(`/tenants/${encodeURIComponent(tenant)}/whatsapp/menus`, payload)
  return res.data
}

export async function publishMenu(tenant: string, menuId: string): Promise<WhatsAppMenu>{
  const res = await api.post(`/tenants/${encodeURIComponent(tenant)}/whatsapp/menus/${encodeURIComponent(menuId)}/publish`)
  return res.data
}

export async function deleteMenu(tenant: string, menuId: string): Promise<{ ok: boolean }>{
  const res = await api.delete(`/tenants/${encodeURIComponent(tenant)}/whatsapp/menus/${encodeURIComponent(menuId)}`)
  return res.data
}

// -------- Triggers API --------

export type TriggerMatch = {
  type: 'exact' | 'prefix' | 'contains' | 'regex'
  value: string
  locale?: string
}

export type TriggerAction =
  | { kind: 'render_submenu'; menu_id: string; node_id?: string }
  | { kind: 'jump_node'; menu_id: string; node_id: string }
  | { kind: 'static_text'; text: string | Record<string, string> }
  | { kind: 'invoke_action'; action_id: string }

export type WhatsAppTrigger = {
  tenant: string
  trigger_id: string
  match: TriggerMatch
  action: TriggerAction
  enabled: boolean
  priority: number
  updated_at?: string
  updated_by?: string
}

export async function listTriggers(tenant: string): Promise<{ items: WhatsAppTrigger[]; total: number }>{
  const res = await api.get(`/tenants/${encodeURIComponent(tenant)}/whatsapp/triggers`)
  return res.data
}

export async function getTrigger(tenant: string, trigger_id: string): Promise<WhatsAppTrigger>{
  const res = await api.get(`/tenants/${encodeURIComponent(tenant)}/whatsapp/triggers`)
  const items = (res.data?.items || []) as WhatsAppTrigger[]
  const found = items.find(t => t.trigger_id === trigger_id)
  if (!found) throw new Error('Trigger not found')
  return found
}

export async function createTrigger(tenant: string, trigger: Omit<WhatsAppTrigger, 'tenant' | 'updated_at' | 'updated_by'>): Promise<WhatsAppTrigger>{
  const res = await api.post(`/tenants/${encodeURIComponent(tenant)}/whatsapp/triggers`, trigger)
  return res.data
}

export async function updateTrigger(tenant: string, trigger_id: string, patch: Partial<WhatsAppTrigger>): Promise<WhatsAppTrigger>{
  const res = await api.patch(`/tenants/${encodeURIComponent(tenant)}/whatsapp/triggers/${encodeURIComponent(trigger_id)}`, patch)
  return res.data
}

export async function deleteTrigger(tenant: string, trigger_id: string): Promise<{ ok: boolean }>{
  const res = await api.delete(`/tenants/${encodeURIComponent(tenant)}/whatsapp/triggers/${encodeURIComponent(trigger_id)}`)
  return res.data
}

// -------- Actions Registry --------

export type WhatsAppActionMeta = {
  id: string
  label: string
  module: string
  requires_caps: string[]
}

export async function listAvailableActions(tenant?: string): Promise<WhatsAppActionMeta[]>{
  const res = await api.get(`/whatsapp/actions`, { params: tenant ? { tenant } : undefined })
  return res.data?.items || []
}

// -------- Tenant custom actions (reusable) --------

export type TenantCustomAction = {
  tenant?: string
  action_id: string
  name: string
  action_type: 'static_text' | 'predefined' | 'workflow'
  text?: string
  system_action_id?: string
  workflow_id?: string
  params?: Record<string, unknown>
  enabled?: boolean
  updated_at?: string
  updated_by?: string
}

export async function listCustomActions(tenant: string): Promise<{ items: TenantCustomAction[]; total: number }>{
  const res = await api.get(`/tenants/${encodeURIComponent(tenant)}/whatsapp/custom-actions`)
  return res.data
}

export async function upsertCustomAction(tenant: string, payload: TenantCustomAction): Promise<TenantCustomAction>{
  const res = await api.post(`/tenants/${encodeURIComponent(tenant)}/whatsapp/custom-actions`, payload)
  return res.data
}

export async function deleteCustomAction(tenant: string, actionId: string): Promise<{ ok: boolean }>{
  const res = await api.delete(`/tenants/${encodeURIComponent(tenant)}/whatsapp/custom-actions/${encodeURIComponent(actionId)}`)
  return res.data
}

export const PLACEHOLDER_HINTS = [
  '{{business_name}}', '{{name}}', '{{phone}}', '{{service}}',
  '{{professional}}', '{{date}}', '{{time}}', '{{appointment_id}}',
]

// Simple helper to test a phrase via dummy Twilio webhook
export async function testTriggerWebhook(toNumber: string, body: string): Promise<string>{
  const res = await api.post(`/integrations/twilio/whatsapp/webhook`, { From: '+911111111111', To: toNumber, Body: body }, { headers: { 'Content-Type': 'application/json' }})
  // Twilio webhook returns XML; axios by default parses text if not JSON
  return typeof res.data === 'string' ? res.data : JSON.stringify(res.data)
}

export async function botNextStep(tenant: string, payload: { phone: string; input: string; menu_id?: string; node?: string; locale?: string; reset_session?: boolean }): Promise<{ reply: string; node: string }>{
  const res = await api.post(`/bot/whatsapp/next`, payload, {
    headers: { 'X-Tenant': tenant }
  })
  return res.data
}
