import { api } from './axios'

export type Slot = { time: string; status: 'available' | 'booked' | 'blocked' }
export type Professional = { 
  name: string; 
  price: number; 
  slots: Slot[]; 
  services?: string[];
  phone?: string;
  degree?: string;
  address?: string;
  bio?: string;
}
export type ProfessionalFull = { 
  tenant?: string; 
  name: string; 
  price?: number; 
  active?: boolean; 
  slots?: Slot[]; 
  services?: string[];
  availability_criteria?: 'daily' | 'weekly' | 'monthly';
  available_days?: number[];
  phone?: string;
  degree?: string;
  address?: string;
  bio?: string;
  created_by?: string | null;
  updated_by?: string | null;
}

export async function listProfessionalNames(tenant: string): Promise<string[]> {
  const res = await api.get(`/tenants/${tenant}/professionals`)
  return res.data as string[]
}

export async function getProfessionalSlots(tenant: string, professional: string): Promise<Slot[]> {
  const res = await api.get(`/tenants/${tenant}/professionals/${encodeURIComponent(professional)}/slots`)
  return res.data as Slot[]
}

export async function createProfessional(
  tenant: string,
  payload: { 
    name: string; 
    price?: number; 
    slots?: Array<string | Slot>; 
    services?: string[];
    phone?: string;
    degree?: string;
    address?: string;
    bio?: string;
  }
): Promise<Professional> {
  const res = await api.post(`/tenants/${tenant}/professionals`, payload)
  return res.data as Professional
}

export async function updateProfessional(
  tenant: string,
  name: string,
  payload: Partial<ProfessionalFull>
): Promise<ProfessionalFull> {
  const res = await api.patch(`/tenants/${tenant}/professionals/${encodeURIComponent(name)}`, payload)
  return res.data as ProfessionalFull
}

export async function updateProfessionalSlots(
  tenant: string,
  professional: string,
  slots: Array<string | Slot>,
  date?: string
): Promise<Professional> {
  const res = await api.put(`/tenants/${tenant}/professionals/${encodeURIComponent(professional)}/slots`, { slots, date })
  return res.data as Professional
}

export async function listProfessionalsFull(
  tenant: string,
  params: { active?: boolean } = {}
): Promise<ProfessionalFull[]> {
  const res = await api.get(`/tenants/${tenant}/professionals/full`, { params })
  return res.data as ProfessionalFull[]
}

export async function setProfessionalActive(
  tenant: string,
  name: string,
  active: boolean
): Promise<ProfessionalFull> {
  const res = await api.patch(`/tenants/${tenant}/professionals/${encodeURIComponent(name)}`, { active })
  return res.data as ProfessionalFull
}
