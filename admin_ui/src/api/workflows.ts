import { api } from './axios'

export type WorkflowStep = {
  action_code: string
  label?: string
  input_required: boolean
  output_key?: string
  ui_type: string
  params?: any
}

export type WorkflowDefinition = {
  tenant: string
  workflow_id: string
  name: string
  steps: WorkflowStep[]
  active: boolean
}

export type WorkflowActionMeta = {
  action_code: string
  label: string
  input_required: boolean
  output_key?: string
  ui_type: string
  description?: string
  module?: string
  group?: string
}

export async function listWorkflows(tenant: string): Promise<{ items: WorkflowDefinition[] }> {
  const res = await api.get(`/tenants/${tenant}/workflows`)
  return res.data
}

export async function getWorkflow(tenant: string, id: string): Promise<WorkflowDefinition> {
  const res = await api.get(`/tenants/${tenant}/workflows/${id}`)
  return res.data
}

export async function upsertWorkflow(tenant: string, wf: WorkflowDefinition) {
  const res = await api.post(`/tenants/${tenant}/workflows`, wf)
  return res.data
}

export async function deleteWorkflow(tenant: string, workflowId: string): Promise<{ ok: boolean }> {
  const res = await api.delete(`/tenants/${encodeURIComponent(tenant)}/workflows/${encodeURIComponent(workflowId)}`)
  return res.data
}

export async function listAvailableWorkflowActions(tenant?: string): Promise<{ items: WorkflowActionMeta[] }> {
  const res = await api.get('/workflows/available-actions', { params: tenant ? { tenant } : undefined })
  return res.data
}

export type WorkflowAuditItem = {
  tenant: string
  workflow_id: string
  name: string
  valid: boolean
  errors: string[]
  repair_available: boolean
  repair_notes: string[]
  errors_after_repair: string[]
}

export async function auditWorkflows(tenant: string): Promise<{ items: WorkflowAuditItem[] }> {
  const res = await api.get(`/tenants/${tenant}/workflows/audit`)
  return res.data
}

export async function repairWorkflows(tenant: string) {
  const res = await api.post(`/tenants/${tenant}/workflows/repair`)
  return res.data
}
