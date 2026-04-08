import { api } from './axios'
import type { PhoneNumberJson } from '../utils/phone'

export type Slot = { time: string; status: 'available' | 'booked' | 'blocked' }
export type ProfessionalBrief = { professional_id: string; name: string; employee_id?: string }
export type Professional = { 
  name: string
  professional_id?: string
  employee_id?: string
  price: number; 
  slots: Slot[]; 
  services?: string[];
  phone?: string;
  degree?: string;
  address?: string;
  bio?: string;
}
export type ProfessionalFull = { 
  tenant?: string
  professional_id?: string
  employee_id?: string
  name: string; 
  price?: number; 
  active?: boolean; 
  slots?: Slot[]; 
  services?: string[];
  availability_criteria?: 'daily' | 'weekly' | 'monthly';
  available_days?: number[];
  phone?: string;
  phone_number?: PhoneNumberJson | null;
  degree?: string;
  address?: string;
  bio?: string;
  created_by?: string | null;
  updated_by?: string | null;
}

/** One row per professional; use ``professional_id`` in API paths (names may repeat). */
export async function listProfessionalBriefs(tenant: string): Promise<ProfessionalBrief[]> {
  const res = await api.get(`/tenants/${tenant}/professionals`)
  return res.data as ProfessionalBrief[]
}

export async function getProfessionalSlots(tenant: string, professional: string): Promise<Slot[]> {
  const res = await api.get(`/tenants/${tenant}/professionals/${encodeURIComponent(professional)}/slots`)
  return res.data as Slot[]
}

export async function createProfessional(
  tenant: string,
  payload: { 
    name: string
    employee_id: string
    price?: number
    slot_interval_minutes?: number
    work_start?: string
    work_end?: string
    availability_criteria?: 'daily' | 'weekly' | 'monthly'
    available_days?: number[]
    services?: string[]
    phone?: string
    degree?: string
    address?: string
    bio?: string
  }
): Promise<Professional> {
  const res = await api.post(`/tenants/${tenant}/professionals`, payload)
  return res.data as Professional
}

export async function updateProfessional(
  tenant: string,
  professionalKey: string,
  payload: Partial<ProfessionalFull>
): Promise<ProfessionalFull> {
  const res = await api.patch(`/tenants/${tenant}/professionals/${encodeURIComponent(professionalKey)}`, payload)
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
  professionalKey: string,
  active: boolean
): Promise<ProfessionalFull> {
  const res = await api.patch(`/tenants/${tenant}/professionals/${encodeURIComponent(professionalKey)}`, { active })
  return res.data as ProfessionalFull
}
