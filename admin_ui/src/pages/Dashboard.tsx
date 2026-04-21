import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboardSummary } from '@api/reports'
import { updateOrderStatus, sendOrderWhatsApp } from '@api/store'
import { useEffectiveTenant } from '../hooks/useEffectiveTenant'
import { useCurrencySymbol } from '../hooks/useTenantDateFormat'
import { PageHeader } from '@components/ui/PageHeader'
import { DataCard } from '@components/ui/DataCard'
import { Alert } from '@components/ui/Alert'

type RecentOrder = {
  id: string
  customer?: { phone?: string; name?: string }
  status?: string
  totals?: { grand_total?: number; subtotal?: number }
}

// ── Sparkline bar chart (revenue trend) ──────────────────────────────────────
function RevenueBarChart({ data, color = '#3b82f6' }: { data: unknown[]; color?: string }) {
  if (!data || data.length === 0) return <span className="text-xs text-[#94a3b8]">No data</span>
  const vals = (data as { total_revenue?: number; date?: string }[]).map((d) => ({
    v: Number(d.total_revenue || 0),
    label: d.date ? String(d.date).slice(5) : '',
  }))
  const maxV = Math.max(1, ...vals.map((d) => d.v))
  return (
    <div className="flex items-end gap-px" style={{ height: 56 }}>
      {vals.map((d, i) => (
        <div
          key={i}
          title={`${d.label}: ${d.v.toLocaleString()}`}
          className="flex-1 rounded-t transition-all"
          style={{
            height: `${Math.max(4, (d.v / maxV) * 100)}%`,
            background: d.v > 0 ? color : '#334155',
            opacity: d.v > 0 ? 0.85 : 0.3,
          }}
        />
      ))}
    </div>
  )
}

// ── KPI stat card ─────────────────────────────────────────────────────────────
function KpiCard({
  label,
  value,
  sub,
  accent,
  to,
}: {
  label: string
  value: string | number
  sub?: string
  accent: string
  to?: string
}) {
  return (
    <DataCard className={`border-l-4 p-4 ${accent}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-[#94a3b8]">{label}</p>
      <p className="mt-1 text-2xl font-bold text-[#f1f5f9]">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-[#64748b]">{sub}</p>}
      {to && (
        <Link to={to} className="mt-2 inline-block text-xs text-[#3b82f6] hover:underline">
          View →
        </Link>
      )}
    </DataCard>
  )
}

// ── Order status badge ────────────────────────────────────────────────────────
function StatusBadge({ status }: { status?: string }) {
  const s = status ?? 'placed'
  const cls =
    s === 'canceled'
      ? 'bg-red-500/20 text-red-300'
      : s === 'confirmed' || s === 'completed'
      ? 'bg-green-500/20 text-green-300'
      : s === 'placed'
      ? 'bg-amber-500/20 text-amber-300'
      : 'bg-[#334155] text-[#94a3b8]'
  return (
    <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium capitalize ${cls}`}>{s}</span>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
export default function Dashboard() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const c = useCurrencySymbol()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [actionOrderId, setActionOrderId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const refreshDashboard = useCallback(() => {
    if (!tenant) return
    getDashboardSummary(tenant)
      .then((d) => { setData(d); setActionError(null) })
      .catch((err: { response?: { data?: { detail?: string } } }) =>
        setError(err?.response?.data?.detail || 'Failed to load dashboard'),
      )
  }, [tenant])

  useEffect(() => {
    if (!tenant) { setLoading(false); setData(null); setError(null); return }
    setLoading(true); setError(null)
    getDashboardSummary(tenant)
      .then(setData)
      .catch((err: { response?: { data?: { detail?: string } } }) =>
        setError(err?.response?.data?.detail || 'Failed to load dashboard'),
      )
      .finally(() => setLoading(false))
  }, [tenant])

  // ── Order actions ───────────────────────────────────────────────────────────
  function extractApiError(e: unknown): string | null {
    if (e && typeof e === 'object' && 'response' in e) {
      const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
      return detail ?? null
    }
    return null
  }

  const handleAcceptOrder = async (orderId: string) => {
    if (!tenant) return
    setActionOrderId(orderId); setActionError(null)
    try { await updateOrderStatus(tenant, orderId, 'confirmed'); refreshDashboard() }
    catch (e: unknown) { setActionError(extractApiError(e) || 'Failed to confirm order') }
    finally { setActionOrderId(null) }
  }

  const handleCancelOrder = async (orderId: string) => {
    if (!tenant) return
    setActionOrderId(orderId); setActionError(null)
    try { await updateOrderStatus(tenant, orderId, 'canceled'); refreshDashboard() }
    catch (e: unknown) { setActionError(extractApiError(e) || 'Failed to cancel order') }
    finally { setActionOrderId(null) }
  }

  const handleSendOrderWhatsApp = async (orderId: string) => {
    if (!tenant) return
    setActionOrderId(orderId); setActionError(null)
    try { await sendOrderWhatsApp(tenant, orderId); refreshDashboard() }
    catch (e: unknown) { setActionError(extractApiError(e) || 'Failed to send WhatsApp') }
    finally { setActionOrderId(null) }
  }

  // ── Loading / error states ─────────────────────────────────────────────────
  if (loading)
    return (
      <div className="p-2">
        <PageHeader title="Dashboard" />
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-24 rounded-xl border border-[#334155] bg-[#1e293b] animate-pulse" />
          ))}
        </div>
        <div className="mb-4 h-40 rounded-xl border border-[#334155] bg-[#1e293b] animate-pulse" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="h-60 rounded-xl border border-[#334155] bg-[#1e293b] animate-pulse" />
          <div className="h-60 rounded-xl border border-[#334155] bg-[#1e293b] animate-pulse" />
        </div>
      </div>
    )

  if (error) return <div className="p-2"><PageHeader title="Dashboard" /><Alert variant="error">{error}</Alert></div>
  if (!tenant) return <div className="p-2"><PageHeader title="Dashboard" /><p className="text-[#cbd5e1]">Select a tenant from the sidebar to view the dashboard.</p></div>
  if (!data) return <div className="p-2"><PageHeader title="Dashboard" /><p className="text-[#cbd5e1]">No dashboard data available.</p></div>

  // ── Data extraction & derived metrics ──────────────────────────────────────
  const modules = (data.modules || []) as string[]
  const capabilities = (data.capabilities || []) as string[]
  const hasStore = modules.includes('store')
  const hasService = modules.includes('salon') || modules.includes('clinic')
  const hasAI = modules.includes('ai')
  const aiNoShowEnabled = hasAI && capabilities.includes('ai.no_show')

  const sales30d = (data.sales_30d || []) as Record<string, unknown>[]
  const totalRevenue30d = Number(data.total_revenue_30d) || 0
  const totalAppts30d = sales30d.reduce((sum, d) => sum + (Number(d.appts_count) || 0), 0)
  const totalOrders30d = sales30d.reduce((sum, d) => sum + (Number(d.orders_count) || 0), 0)

  const professionalPerformance = (data.professional_performance || []) as {
    professional: string; revenue?: number; completed?: number; canceled?: number
  }[]
  const topSellers = (data.top_sellers || []) as { sku: string; name: string; qty?: number; revenue?: number }[]
  const lowStock = (data.low_stock || []) as { sku: string; name: string; available_qty?: number; days_to_stockout?: number }[]
  const recentOrders = (data.recent_orders || []) as RecentOrder[]
  const noShowBlockedCount = Number(data.no_show_blocked_count) || 0
  const noShowTotalCount = Number(data.no_show_total_count) || 0
  const pendingOrdersCount = Number(data.pending_orders_count) || 0
  const totalCustomers = Number(data.total_customers) || 0
  const newCustomers30d = Number(data.new_customers_30d) || 0

  // Derived: cancellation rate from professional performance
  const totalCompleted = professionalPerformance.reduce((s, p) => s + (Number(p.completed) || 0), 0)
  const totalCanceled = professionalPerformance.reduce((s, p) => s + (Number(p.canceled) || 0), 0)
  const cancellationRate = totalCompleted + totalCanceled > 0
    ? Math.round((totalCanceled / (totalCompleted + totalCanceled)) * 100)
    : null

  // Derived: avg appointment value
  const avgApptValue = totalAppts30d > 0 ? Math.round(totalRevenue30d / totalAppts30d) : null

  // Derived: avg daily revenue
  const avgDailyRevenue = sales30d.length > 0 ? Math.round(totalRevenue30d / sales30d.length) : 0

  // Top professional (by revenue)
  const topPro = professionalPerformance.length > 0 ? professionalPerformance[0] : null

  return (
    <div className="p-2">
      <PageHeader
        title="Dashboard"
        actions={
          <div className="flex flex-wrap gap-1.5">
            {modules.map((m) => (
              <span key={m} className="rounded-md border border-[#334155] px-2 py-0.5 text-xs text-[#cbd5e1] capitalize">{m}</span>
            ))}
          </div>
        }
      />

      {/* ── Section 1: KPI Cards ────────────────────────────────────────── */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
        {/* Revenue — always shown */}
        <KpiCard
          label="30d Revenue"
          value={`${c}${totalRevenue30d.toLocaleString()}`}
          sub={`Avg ${c}${avgDailyRevenue.toLocaleString()}/day`}
          accent="border-l-[#3b82f6]"
        />

        {/* Appointments — service tenants only */}
        {hasService && (
          <KpiCard
            label="30d Appointments"
            value={totalAppts30d}
            sub={cancellationRate !== null ? `${cancellationRate}% cancellation rate` : 'Total bookings'}
            accent="border-l-[#10b981]"
            to="/appointments"
          />
        )}

        {/* Avg Appointment Value — service tenants only */}
        {hasService && avgApptValue !== null && (
          <KpiCard
            label="Avg Appointment"
            value={`${c}${avgApptValue.toLocaleString()}`}
            sub="Average revenue per booking"
            accent="border-l-[#06b6d4]"
          />
        )}

        {/* Orders — store tenants only */}
        {hasStore && (
          <KpiCard
            label="30d Orders"
            value={totalOrders30d}
            sub={pendingOrdersCount > 0 ? `${pendingOrdersCount} pending confirmation` : 'Completed orders'}
            accent={pendingOrdersCount > 0 ? 'border-l-[#f59e0b]' : 'border-l-[#8b5cf6]'}
            to={pendingOrdersCount > 0 ? '/store/orders' : undefined}
          />
        )}

        {/* Customers — always shown */}
        <KpiCard
          label="Customers"
          value={totalCustomers.toLocaleString()}
          sub={newCustomers30d > 0 ? `+${newCustomers30d} new this month` : 'Total registered'}
          accent="border-l-[#ec4899]"
          to="/customers"
        />

        {/* Low Stock — store only */}
        {hasStore && lowStock.length > 0 && (
          <KpiCard
            label="Low Stock Alerts"
            value={lowStock.length}
            sub="Products running low"
            accent="border-l-[#eab308]"
            to="/store/products"
          />
        )}

        {/* No-Show Tracker — AI+service only */}
        {hasService && aiNoShowEnabled && (
          <KpiCard
            label="No-Show Tracker"
            value={noShowTotalCount || noShowBlockedCount}
            sub={noShowBlockedCount > 0 ? `${noShowBlockedCount} currently blocked` : 'Customers tracked'}
            accent={noShowBlockedCount > 0 ? 'border-l-[#ef4444]' : 'border-l-[#f59e0b]'}
            to="/no-show-blocked"
          />
        )}
      </div>

      {/* ── Section 2: Revenue Trend (full width) ──────────────────────── */}
      <DataCard className="mb-6 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-[#f1f5f9]">Revenue Trend — Last 30 Days</h2>
            <p className="text-xs text-[#64748b]">Daily revenue bars · hover for exact value</p>
          </div>
          <div className="flex flex-wrap gap-4 text-right">
            <div>
              <p className="text-xs text-[#64748b]">Total</p>
              <p className="text-lg font-bold text-[#f1f5f9]">{c}{totalRevenue30d.toLocaleString()}</p>
            </div>
            {hasService && totalAppts30d > 0 && (
              <div>
                <p className="text-xs text-[#64748b]">Appointments</p>
                <p className="text-lg font-bold text-[#10b981]">{totalAppts30d}</p>
              </div>
            )}
            {hasStore && totalOrders30d > 0 && (
              <div>
                <p className="text-xs text-[#64748b]">Orders</p>
                <p className="text-lg font-bold text-[#8b5cf6]">{totalOrders30d}</p>
              </div>
            )}
          </div>
        </div>
        <RevenueBarChart data={sales30d} color="#3b82f6" />
        {/* X-axis day labels — first, mid, last */}
        {sales30d.length > 0 && (
          <div className="mt-1 flex justify-between text-[10px] text-[#475569]">
            <span>{String((sales30d[0] as { date?: string }).date ?? '').slice(5)}</span>
            <span>{String((sales30d[Math.floor(sales30d.length / 2)] as { date?: string }).date ?? '').slice(5)}</span>
            <span>{String((sales30d[sales30d.length - 1] as { date?: string }).date ?? '').slice(5)}</span>
          </div>
        )}
      </DataCard>

      {/* ── Section 3: Performance tables ──────────────────────────────── */}
      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Professional Performance */}
        {hasService && professionalPerformance.length > 0 && (
          <DataCard className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-[#f1f5f9]">Professional Performance (30d)</h2>
              {topPro && (
                <span className="rounded bg-[#3b82f6]/20 px-2 py-0.5 text-xs text-[#93c5fd]">
                  🏆 {topPro.professional}
                </span>
              )}
            </div>
            <div className="space-y-3">
              {professionalPerformance.slice(0, 6).map((p) => {
                const total = (p.completed ?? 0) + (p.canceled ?? 0)
                const rate = total > 0 ? Math.round(((p.completed ?? 0) / total) * 100) : 0
                return (
                  <div key={p.professional}>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-[#f1f5f9]">{p.professional}</span>
                      <span className="text-sm font-semibold text-[#f1f5f9]">{c}{(p.revenue ?? 0).toLocaleString()}</span>
                    </div>
                    <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[#334155]">
                      <div
                        className="h-full rounded-full bg-[#3b82f6]"
                        style={{ width: `${Math.min(100, ((p.revenue ?? 0) / (totalRevenue30d || 1)) * 100)}%` }}
                      />
                    </div>
                    <div className="mt-1 flex gap-3 text-xs">
                      <span className="text-[#10b981]">✓ {p.completed ?? 0} completed</span>
                      <span className="text-[#f87171]">✗ {p.canceled ?? 0} canceled</span>
                      <span className="text-[#64748b]">{rate}% completion</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </DataCard>
        )}

        {/* Top Selling Products */}
        {hasStore && (
          <DataCard className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-[#f1f5f9]">Top Selling Products (30d)</h2>
              <Link to="/store/products" className="text-xs text-[#3b82f6] hover:underline">All products →</Link>
            </div>
            {topSellers.length === 0 ? (
              <p className="text-sm text-[#64748b]">No sales recorded yet.</p>
            ) : (
              <div className="space-y-2.5">
                {topSellers.map((s, idx) => (
                  <div key={s.sku} className="flex items-center gap-3">
                    <span className="w-5 shrink-0 text-center text-xs font-bold text-[#475569]">#{idx + 1}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-[#f1f5f9]">{s.name}</p>
                      <p className="text-xs text-[#64748b]">SKU: {s.sku}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="text-sm font-semibold text-[#f1f5f9]">{s.qty ?? 0} sold</p>
                      <p className="text-xs text-[#94a3b8]">{c}{(s.revenue ?? 0).toLocaleString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </DataCard>
        )}

        {/* Customer Insights — show when no performance tables fill the row */}
        {!hasService && !hasStore && (
          <DataCard className="p-4">
            <h2 className="mb-3 text-base font-semibold text-[#f1f5f9]">Customer Insights</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg bg-[#1e293b] px-3 py-2">
                <span className="text-sm text-[#94a3b8]">Total Customers</span>
                <span className="text-lg font-bold text-[#f1f5f9]">{totalCustomers.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between rounded-lg bg-[#1e293b] px-3 py-2">
                <span className="text-sm text-[#94a3b8]">New This Month</span>
                <span className="text-lg font-bold text-[#10b981]">+{newCustomers30d}</span>
              </div>
            </div>
          </DataCard>
        )}
      </div>

      {/* ── Section 4: Recent Orders (store only) ──────────────────────── */}
      {hasStore && (
        <DataCard className="mb-6 p-4">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-3">
              <h2 className="text-base font-semibold text-[#f1f5f9]">Recent Orders</h2>
              {pendingOrdersCount > 0 && (
                <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-xs font-semibold text-amber-300">
                  {pendingOrdersCount} pending
                </span>
              )}
            </div>
            <Link to="/store/orders" className="text-xs text-[#3b82f6] hover:underline">View all →</Link>
          </div>
          {actionError && (
            <div className="mb-2 rounded border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm text-red-300">{actionError}</div>
          )}
          {recentOrders.length === 0 ? (
            <p className="text-sm text-[#64748b]">No orders yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead>
                  <tr className="border-b border-[#334155] text-[#64748b]">
                    <th className="py-2 pr-3 font-medium">Order</th>
                    <th className="py-2 pr-3 font-medium">Customer</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 pr-3 text-right font-medium">Total</th>
                    <th className="py-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recentOrders.map((o) => {
                    const phone = o.customer?.phone ?? '—'
                    const name = o.customer?.name
                    const canSendWA = phone && phone !== 'catalog'
                    const total = o.totals?.grand_total ?? o.totals?.subtotal ?? 0
                    const isPlaced = o.status === 'placed' || !o.status
                    const isCanceled = o.status === 'canceled'
                    const busy = actionOrderId === o.id
                    return (
                      <tr key={o.id} className="border-b border-[#334155]/40 hover:bg-[#1e293b]/50">
                        <td className="py-2 pr-3 font-mono text-xs text-[#94a3b8]">{o.id}</td>
                        <td className="py-2 pr-3 text-[#cbd5e1]">
                          {name ? <span>{name}<br /><span className="text-xs text-[#475569]">{phone}</span></span> : phone}
                        </td>
                        <td className="py-2 pr-3"><StatusBadge status={o.status} /></td>
                        <td className="py-2 pr-3 text-right font-semibold text-[#e2e8f0]">{c}{Number(total).toLocaleString()}</td>
                        <td className="py-2">
                          <div className="flex flex-wrap gap-1">
                            {isPlaced && (
                              <button type="button" onClick={() => handleAcceptOrder(o.id)} disabled={busy}
                                className="rounded bg-green-600 px-2 py-0.5 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50">
                                Confirm
                              </button>
                            )}
                            {!isCanceled && (
                              <button type="button" onClick={() => handleCancelOrder(o.id)} disabled={busy}
                                className="rounded bg-red-600/80 px-2 py-0.5 text-xs font-medium text-white hover:bg-red-500 disabled:opacity-50">
                                Cancel
                              </button>
                            )}
                            {canSendWA && (
                              <button type="button" onClick={() => handleSendOrderWhatsApp(o.id)} disabled={busy}
                                className="rounded bg-[#25D366] px-2 py-0.5 text-xs font-medium text-white hover:bg-[#20bd5a] disabled:opacity-50">
                                WhatsApp
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </DataCard>
      )}

      {/* ── Section 5: Inventory Alerts (store only) ───────────────────── */}
      {hasStore && lowStock.length > 0 && (
        <DataCard className="mb-6 border-l-4 border-l-[#eab308] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold text-[#fde047]">⚠ Inventory Alerts</h2>
            <Link to="/store/products" className="text-xs text-[#3b82f6] hover:underline">Manage stock →</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[360px] text-left text-sm">
              <thead>
                <tr className="border-b border-[#334155] text-[#64748b]">
                  <th className="py-1.5 pr-3 font-medium">Product</th>
                  <th className="py-1.5 pr-3 font-medium">SKU</th>
                  <th className="py-1.5 pr-3 text-right font-medium">Stock Left</th>
                  <th className="py-1.5 text-right font-medium">Days to Stockout</th>
                </tr>
              </thead>
              <tbody>
                {lowStock.map((item) => (
                  <tr key={item.sku} className="border-b border-[#334155]/40">
                    <td className="py-1.5 pr-3 text-[#f1f5f9]">{item.name}</td>
                    <td className="py-1.5 pr-3 font-mono text-xs text-[#94a3b8]">{item.sku}</td>
                    <td className="py-1.5 pr-3 text-right font-semibold text-[#fde047]">{item.available_qty ?? 0}</td>
                    <td className="py-1.5 text-right">
                      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                        (item.days_to_stockout ?? 99) <= 3 ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'
                      }`}>
                        {item.days_to_stockout ?? '?'}d
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataCard>
      )}

      {/* ── Section 6: Quick links ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* AI Hub */}
        {hasAI && (
          <DataCard className="p-4">
            <h2 className="mb-1 text-base font-semibold text-[#f1f5f9]">AI & Predictions</h2>
            <p className="mb-3 text-xs text-[#64748b]">No-show risk, slot recommendations, low-stock forecast, and more.</p>
            <div className="flex flex-wrap gap-2">
              <Link to="/ai" className="rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">AI Hub</Link>
              <Link to="/ai/appointments" className="rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Appointments Assist</Link>
              {hasStore && <Link to="/store/catalog" className="rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Store Catalog</Link>}
            </div>
          </DataCard>
        )}

        {/* Reports quick link */}
        <DataCard className="p-4">
          <h2 className="mb-1 text-base font-semibold text-[#f1f5f9]">Quick Links</h2>
          <p className="mb-3 text-xs text-[#64748b]">Jump to key sections.</p>
          <div className="flex flex-wrap gap-2">
            <Link to="/reports" className="rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Reports</Link>
            <Link to="/customers" className="rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Customers</Link>
            {hasService && <Link to="/appointments" className="rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Appointments</Link>}
            {hasStore && <Link to="/store/orders" className="rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Orders</Link>}
            <Link to="/settings" className="rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Settings</Link>
          </div>
        </DataCard>
      </div>
    </div>
  )
}
