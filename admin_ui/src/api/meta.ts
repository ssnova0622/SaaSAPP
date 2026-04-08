import { api } from './axios'

export type CountryOption = {
  iso2: string
  name: string
  dial: string
}

export async function listCountries(): Promise<{ items: CountryOption[] }> {
  const res = await api.get<{ items: CountryOption[] }>('/meta/countries')
  return res.data
}
