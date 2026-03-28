import { api } from './axios'
import { getApiBaseURL } from './config'

export async function uploadFile(tenant: string, file: File): Promise<{ url: string; filename: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post<{ url: string; filename: string }>(`/tenants/${tenant}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

/**
 * Upload a product/variant image. Stored in media_storage/{tenant}/ (or S3 when enabled).
 * Returns path like /v1/media/{tenant}/{filename} to store in product.image_url.
 */
export async function uploadProductMedia(tenant: string, file: File): Promise<{ url: string; filename: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post<{ url: string; filename: string }>(`/tenants/${tenant}/media/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

/** Build a full URL for an uploaded file (for WhatsApp, etc.). Backend returns path like /v1/uploads/tenant/filename. */
export function fullUrlForUpload(pathOrUrl: string): string {
  if (pathOrUrl.startsWith('http')) return pathOrUrl
  const base = getApiBaseURL().replace(/\/v1$/, '')
  return base + (pathOrUrl.startsWith('/') ? pathOrUrl : '/' + pathOrUrl)
}

/** Build full URL for product media (image_url). Path is like /v1/media/tenant/filename. */
export function fullUrlForMedia(pathOrUrl: string): string {
  if (!pathOrUrl) return ''
  if (pathOrUrl.startsWith('http')) return pathOrUrl
  if (pathOrUrl.startsWith('data:')) return pathOrUrl
  const base = getApiBaseURL().replace(/\/v1$/, '')
  return base + (pathOrUrl.startsWith('/') ? pathOrUrl : '/' + pathOrUrl)
}
