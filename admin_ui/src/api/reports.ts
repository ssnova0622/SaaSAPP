import { api } from './axios'
import { getApiBaseURL } from './config'

export type ReportDoc = {
  tenant: string
  date: string
  storage: string
  url_type: 's3' | 'file'
  url?: string
  created_at?: string
  sent_via?: string[]
  status?: string
}

export type PeriodSummaryResponse = {
  tenant: string
  /** ISO 4217; matches tenant payment_config.currency */
  currency?: string
  modules: string[]
  period: { from: string; to: string; label: string }
  kpis: {
    total_revenue: number
    store_revenue: number
    service_revenue: number
    orders_count: number
    units_sold: number
    appointments_count: number
    new_customers: number
    returning_customers: number
  }
  highlights: string[]
  order_status_breakdown: { status: string; count: number }[]
}

export async function getPeriodSummary(
  tenant: string,
  params: { days?: number; from_date?: string; to_date?: string } = {},
): Promise<PeriodSummaryResponse> {
  const res = await api.get(`/tenants/${tenant}/reports/period_summary`, { params })
  return res.data as PeriodSummaryResponse
}

export async function listReports(tenant: string, params: { page?: number; size?: number; from_date?: string; to_date?: string } = {}) {
  const res = await api.get(`/tenants/${tenant}/reports/daily`, { params })
  return res.data as { items: ReportDoc[]; total: number; page: number; size: number }
}

export async function runReport(tenant: string, fromDate?: string, toDate?: string) {
  const res = await api.post(`/tenants/${tenant}/reports/daily/run`, null, { params: { date_str: fromDate, to_date_str: toDate } })
  return res.data as ReportDoc
}

export function reportDownloadUrl(tenant: string, date: string): string {
  const base = getApiBaseURL()
  return `${base}/tenants/${encodeURIComponent(tenant)}/reports/${encodeURIComponent(date)}/download`
}

export async function downloadReportAsBlob(tenant: string, date: string): Promise<string> {
  const url = reportDownloadUrl(tenant, date)
  // Server may generate the PDF on first download (large ranges can take a while)
  const res = await api.get(url, { responseType: 'blob', timeout: 120000 })
  return URL.createObjectURL(res.data)
}

/** Download PDF with a sensible filename (avoids a blank tab when the browser treats the blob as PDF). */
export async function downloadReportFile(tenant: string, date: string): Promise<void> {
  const blobUrl = await downloadReportAsBlob(tenant, date)
  const safe = date.replace(/_to_/g, '-to-').replace(/[^a-zA-Z0-9-]/g, '_')
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = `business-report-${safe}.pdf`
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(blobUrl)
}

// ---- Analytics for graphs ----
export type SalesPoint = {
  date: string;
  orders_count: number;
  units: number;
  store_revenue: number;
  appts_count: number;
  service_revenue: number;
  total_revenue: number;
}
export type SalesTimeseriesResponse = { items: SalesPoint[]; days: number; interval: 'day' }

export async function getSalesTimeseries(
  tenant: string,
  params: { days?: number; interval?: 'day'; from_date?: string; to_date?: string } = {}
): Promise<SalesTimeseriesResponse> {
  const res = await api.get(`/tenants/${tenant}/reports/sales_timeseries`, { params })
  return res.data as SalesTimeseriesResponse
}

export type ProfessionalPerformanceRow = {
  professional: string;
  appointments: number;
  completed: number;
  revenue: number;
  canceled: number;
}

export async function getProfessionalPerformance(
  tenant: string,
  params: { days?: number; from_date?: string; to_date?: string } = {}
): Promise<{ items: ProfessionalPerformanceRow[]; days: number }> {
  const res = await api.get(`/tenants/${tenant}/reports/professional_performance`, { params })
  return res.data
}

export async function getDashboardSummary(tenant: string): Promise<any> {
  const res = await api.get(`/tenants/${tenant}/dashboard/summary`)
  return res.data
}

export type StatusRow = { status: string; count: number }
export type OrdersByStatusResponse = { items: StatusRow[]; days: number }

export async function getOrdersByStatus(
  tenant: string,
  params: { days?: number; from_date?: string; to_date?: string } = {}
): Promise<OrdersByStatusResponse> {
  const res = await api.get(`/tenants/${tenant}/reports/orders_by_status`, { params })
  return res.data as OrdersByStatusResponse
}

export type CategoryRow = { category: string; qty: number; revenue: number; share_revenue: number }
export type CategoryMixResponse = { items: CategoryRow[]; days: number }

export async function getCategoryMix(
  tenant: string,
  params: { days?: number; from_date?: string; to_date?: string } = {}
): Promise<CategoryMixResponse> {
  const res = await api.get(`/tenants/${tenant}/reports/category_mix`, { params })
  return res.data as CategoryMixResponse
}

export type CustomersPoint = { date: string; new_customers: number; returning_customers: number }
export type CustomersTimeseriesResponse = { items: CustomersPoint[]; days: number }

export async function getCustomersTimeseries(
  tenant: string,
  params: { days?: number; from_date?: string; to_date?: string } = {}
): Promise<CustomersTimeseriesResponse> {
  const res = await api.get(`/tenants/${tenant}/reports/customers_timeseries`, { params })
  return res.data as CustomersTimeseriesResponse
}
