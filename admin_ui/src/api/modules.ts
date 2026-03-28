import { api } from './axios'

export type RegistryItem = {
  id: string
  type: 'module' | 'capability'
  group: string
  label: string
  description?: string
  dependsOn?: string[]
  default?: boolean
  /** For capabilities: owning module id (e.g. salon, core) */
  module?: string
}

export async function listRegistry(): Promise<{ items: RegistryItem[] }> {
  const res = await api.get('/modules')
  return res.data as { items: RegistryItem[] }
}
