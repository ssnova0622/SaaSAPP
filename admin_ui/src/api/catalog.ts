import { api } from './axios'

// ---- Categories ----
export type Category = { name: string; active: boolean; created_by?: string | null; updated_by?: string | null }

export async function listCategories(tenant: string): Promise<Category[]> {
  const res = await api.get(`/tenants/${tenant}/catalog/categories`)
  return res.data as Category[]
}

export async function upsertCategory(tenant: string, payload: Category): Promise<Category> {
  const res = await api.post(`/tenants/${tenant}/catalog/categories`, payload)
  return res.data as Category
}

export async function patchCategory(tenant: string, name: string, active: boolean): Promise<Category> {
  const res = await api.patch(`/tenants/${tenant}/catalog/categories/${encodeURIComponent(name)}`, { active })
  return res.data as Category
}

export async function deleteCategory(tenant: string, name: string): Promise<void> {
  await api.delete(`/tenants/${tenant}/catalog/categories/${encodeURIComponent(name)}`)
}

// ---- Products ----
export type Product = {
  sku: string
  name: string
  category?: string | null
  price: number
  mrp?: number | null
  tax?: number | null
  unit?: string | null
  active: boolean
  barcode?: string | null
  image_url?: string | null
  /** Ordered list of product image URLs (gallery) */
  image_urls?: string[] | null
  /** Product description / details text */
  description?: string | null
  discount_type?: 'amount' | 'percent' | null
  discount_value?: number | null
  /** Minimum selling price (MSP) floor; offers/cart cannot go below this */
  minimum_selling_price?: number | null
  /** Final selling price (Selling − Discount + VAT), stored on save */
  final_selling_price?: number | null
  /** If set, minimum_selling_price is auto-calculated from cost + margin */
  margin_type?: 'percent' | 'amount' | null
  margin_value?: number | null
  unit_conversions?: Array<{ unit: string; factor: number }> | null
  // Present when response is a flattened variant row
  attributes?: Record<string, string> | null
  created_by?: string | null
  updated_by?: string | null
  // When listing base products, variants may be present as embedded list
  variants?: Array<{
    variant_sku: string
    attributes: Record<string, string>
    price?: number | null
    mrp?: number | null
    tax?: number | null
    discount_type?: 'amount' | 'percent' | null
    discount_value?: number | null
    image_url?: string | null
    active?: boolean | null
  }> | null
}

export async function listProducts(
  tenant: string,
  params: { search?: string; category?: string; active?: boolean; page?: number; size?: number; flatten_variants?: boolean } = {}
): Promise<{ items: Product[]; total: number; page: number; size: number }> {
  const res = await api.get(`/tenants/${tenant}/catalog/products`, { params })
  return res.data
}

/** List active products (no auth). Use as fallback when catalog list fails (e.g. capability). */
export async function listProductsPublic(
  tenant: string,
  params: { search?: string; category?: string; page?: number; size?: number } = {}
): Promise<{ items: Product[]; total: number; page: number; size: number }> {
  const res = await api.get(`/tenants/${tenant}/products/public`, { params })
  return res.data
}

/** List popular/best-selling products (no auth). For catalog "popular first" section. */
export async function listPopularProductsPublic(
  tenant: string,
  params: { top?: number; days?: number } = {}
): Promise<{ items: Product[]; total: number }> {
  const res = await api.get(`/tenants/${tenant}/products/public/popular`, { params })
  return res.data
}

/** List active category names (no auth). For catalog filter. */
export async function listCategoriesPublic(tenant: string): Promise<{ items: { name: string }[]; total: number }> {
  const res = await api.get(`/tenants/${tenant}/categories/public`)
  return res.data
}

/** Tenant public info for catalog (business name, WhatsApp number, currency). No auth. */
export async function getTenantPublicInfo(tenant: string): Promise<{ name: string; whatsapp_number: string | null; currency?: string }> {
  const res = await api.get(`/tenants/${tenant}/public/info`)
  return res.data
}

/** Create order from catalog cart (no auth). Returns order_id for including in WhatsApp message. Optional customer_phone for testing (e.g. dummy number on localhost). */
export async function createOrderFromCatalog(
  tenant: string,
  items: Array<{ sku: string; name?: string; qty: number; price_snapshot: number; unit?: string }>,
  options?: { customer_phone?: string }
): Promise<{ order_id: string; status: string; total: number }> {
  const body: { items: typeof items; customer_phone?: string } = { items }
  if (options?.customer_phone) body.customer_phone = options.customer_phone
  const res = await api.post(`/tenants/${tenant}/orders/from-catalog`, body)
  return res.data
}

export async function upsertProduct(tenant: string, payload: Product): Promise<Product> {
  const res = await api.post(`/tenants/${tenant}/catalog/products`, payload)
  return res.data as Product
}

export async function updateProduct(tenant: string, sku: string, payload: Product): Promise<Product> {
  const res = await api.put(`/tenants/${tenant}/catalog/products/${encodeURIComponent(sku)}`, payload)
  return res.data as Product
}

export async function deleteProduct(tenant: string, sku: string): Promise<void> {
  await api.delete(`/tenants/${tenant}/catalog/products/${encodeURIComponent(sku)}`)
}

export async function getProductBySku(tenant: string, sku: string): Promise<Product> {
  const res = await api.get(`/tenants/${tenant}/catalog/products/by-sku/${encodeURIComponent(sku)}`)
  return res.data as Product
}

// ---- Inventory ----
export async function getInventory(tenant: string, sku: string): Promise<{ sku: string; available_qty: number }> {
  const res = await api.get(`/tenants/${tenant}/inventory/${encodeURIComponent(sku)}`)
  return res.data as { sku: string; available_qty: number }
}

export async function setInventory(tenant: string, sku: string, available_qty: number): Promise<{ sku: string; available_qty: number }> {
  const res = await api.put(`/tenants/${tenant}/inventory/${encodeURIComponent(sku)}`, { sku, available_qty })
  return res.data as { sku: string; available_qty: number }
}
