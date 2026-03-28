import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getDashboardSummary } from '@api/reports'
import { updateOrderStatus, sendOrderWhatsApp } from '@api/store'
import { useEffectiveTenant } from '../hooks/useEffectiveTenant'
import { PageHeader } from '@components/ui/PageHeader'
import { DataCard } from '@components/ui/DataCard'
import { Alert } from '@components/ui/Alert'

type RecentOrder = {
  id: string
  customer?: { phone?: string; name?: string }
  status?: string
  totals?: { grand_total?: number; subtotal?: number }
}

function MiniRevenueChart({ data, color = '#3b82f6' }: { data: unknown[]; color?: string }) {
  const width = 400
  const height = 100
  const pad = 5
  if (!data || data.length < 2) return <span className="text-xs text-[#94a3b8]">Insufficient data</span>
  const vals = (data as { total_revenue?: number }[]).map((d) => Number(d.total_revenue || 0))
  const maxV = Math.max(1, ...vals)
  const stepX = (width - 2 * pad) / (vals.length - 1)
  const scaleY = (v: number) => height - pad - (v / maxV) * (height - 2 * pad)
  const d = vals.map((v, i) => `${i === 0 ? 'M' : 'L'} ${pad + i * stepX} ${scaleY(v)}`).join(' ')
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <path d={`${d} L ${width - pad} ${height - pad} L ${pad} ${height - pad} Z`} fill={color} opacity={0.1} />
      <path d={d} fill="none" stroke={color} strokeWidth={2} />
    </svg>
  )
}

export default function Dashboard() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [actionOrderId, setActionOrderId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const refreshDashboard = useCallback(() => {
    if (!tenant) return
    getDashboardSummary(tenant)
      .then((d) => { setData(d); setActionError(null) })
      .catch((err: { response?: { data?: { detail?: string } } }) => setError(err?.response?.data?.detail || 'Failed to load dashboard'))
  }, [tenant])

  useEffect(() => {
    if (!tenant) {
      setLoading(false)
      setData(null)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    getDashboardSummary(tenant)
      .then(setData)
      .catch((err: { response?: { data?: { detail?: string } } }) => setError(err?.response?.data?.detail || 'Failed to load dashboard'))
      .finally(() => setLoading(false))
  }, [tenant])

  if (loading)
    return (
      <div className="p-2">
        <PageHeader title="Dashboard" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-36 rounded-xl border border-[#334155] bg-[#1e293b] animate-pulse" />
          ))}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="h-72 rounded-xl border border-[#334155] bg-[#1e293b] animate-pulse" />
          <div className="h-72 rounded-xl border border-[#334155] bg-[#1e293b] animate-pulse" />
        </div>
      </div>
    )

  if (error) return <div className="p-2"><PageHeader title="Dashboard" /><Alert variant="error">{error}</Alert></div>
  if (!tenant) return <div className="p-2"><PageHeader title="Dashboard" /><p className="text-[#cbd5e1]">Select a tenant from the sidebar to view the dashboard.</p></div>
  if (!data) return <div className="p-2"><PageHeader title="Dashboard" /><p className="text-[#cbd5e1]">No dashboard data available.</p></div>

  const modules = (data.modules || []) as string[]
  const capabilities = (data.capabilities || []) as string[]
  const hasStore = modules.includes('store')
  const hasService = modules.includes('salon') || modules.includes('clinic')
  const hasAI = modules.includes('ai')
  const aiNoShowEnabled = hasAI && capabilities.includes('ai.no_show')
  const sales30d = (data.sales_30d || []) as Record<string, unknown>[]
  const totalRevenue30d = Number(data.total_revenue_30d) || 0
  const professionalPerformance = (data.professional_performance || []) as { professional: string; revenue?: number; completed?: number; canceled?: number }[]
  const topSellers = (data.top_sellers || []) as { sku: string; name: string; qty?: number; revenue?: number }[]
  const lowStock = (data.low_stock || []) as { sku: string; name: string; available_qty?: number; days_to_stockout?: number }[]
  const noShowBlockedCount = Number(data.no_show_blocked_count) || 0
  const totalAppts30d = sales30d.reduce((sum, d) => sum + (Number(d.appts_count) || 0), 0)
  const totalOrders30d = sales30d.reduce((sum, d) => sum + (Number(d.orders_count) || 0), 0)
  const recentOrders = (data.recent_orders || []) as RecentOrder[]

  const handleAcceptOrder = async (orderId: string) => {
    if (!tenant) return
    setActionOrderId(orderId)
    setActionError(null)
    try {
      await updateOrderStatus(tenant, orderId, 'confirmed')
      refreshDashboard()
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setActionError(msg || 'Failed to confirm order')
    } finally {
      setActionOrderId(null)
    }
  }

  const handleCancelOrder = async (orderId: string) => {
    if (!tenant) return
    setActionOrderId(orderId)
    setActionError(null)
    try {
      await updateOrderStatus(tenant, orderId, 'canceled')
      refreshDashboard()
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setActionError(msg || 'Failed to cancel order')
    } finally {
      setActionOrderId(null)
    }
  }

  const handleSendOrderWhatsApp = async (orderId: string) => {
    if (!tenant) return
    setActionOrderId(orderId)
    setActionError(null)
    try {
      await sendOrderWhatsApp(tenant, orderId)
      refreshDashboard()
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'response' in e && (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
      setActionError(msg || 'Failed to send WhatsApp')
    } finally {
      setActionOrderId(null)
    }
  }

  return (
    <div className="p-2">
      <PageHeader
        title={`Dashboard`}
        actions={
          <div className="flex flex-wrap gap-2">
            {modules.map((m) => (
              <span key={m} className="rounded-md border border-[#334155] px-2 py-0.5 text-xs text-[#cbd5e1]">{m}</span>
            ))}
          </div>
        }
      />

      {/* Quick KPIs */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-2 md:grid-cols-4">
        <DataCard className="border-l-4 border-l-[#3b82f6] p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-[#94a3b8]">30d Revenue</p>
          <p className="mt-1 text-2xl font-bold text-[#f1f5f9]">₹{totalRevenue30d.toLocaleString()}</p>
        </DataCard>
        {hasService && (
          <DataCard className="border-l-4 border-l-[#10b981] p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[#94a3b8]">30d Appointments</p>
            <p className="mt-1 text-2xl font-bold text-[#f1f5f9]">{totalAppts30d}</p>
          </DataCard>
        )}
        {hasStore && (
          <DataCard className="border-l-4 border-l-[#8b5cf6] p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[#94a3b8]">30d Orders</p>
            <p className="mt-1 text-2xl font-bold text-[#f1f5f9]">{totalOrders30d}</p>
          </DataCard>
        )}
        {hasService && aiNoShowEnabled && (
          <DataCard className="border-l-4 border-l-[#f59e0b] p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-[#94a3b8]">No-Show Blocked</p>
            <p className="mt-1 text-2xl font-bold text-[#f1f5f9]">{noShowBlockedCount}</p>
            {noShowBlockedCount > 0 && (
              <Link to="/no-show-blocked" className="mt-2 inline-block text-xs text-[#3b82f6] hover:underline">View list →</Link>
            )}
          </DataCard>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <DataCard className="p-4">
          <p className="text-xs text-[#94a3b8]">30d Revenue</p>
          <p className="my-1 text-2xl font-semibold text-[#f1f5f9]">₹{totalRevenue30d.toLocaleString()}</p>
          <MiniRevenueChart data={sales30d} />
        </DataCard>
        {hasService && (
          <DataCard className="p-4">
            <p className="text-xs text-[#94a3b8]">30d Appointments</p>
            <p className="my-1 text-2xl font-semibold text-[#f1f5f9]">
              {sales30d.reduce((sum, d) => sum + (Number(d.appts_count) || 0), 0)}
            </p>
            <p className="text-xs text-[#94a3b8]">Total bookings in last 30 days</p>
          </DataCard>
        )}
        {hasStore && (
          <DataCard className="p-4">
            <p className="text-xs text-[#94a3b8]">30d Store Orders</p>
            <p className="my-1 text-2xl font-semibold text-[#f1f5f9]">
              {sales30d.reduce((sum, d) => sum + (Number(d.orders_count) || 0), 0)}
            </p>
            <p className="text-xs text-[#94a3b8]">Successful orders in last 30 days</p>
          </DataCard>
        )}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        {hasService && professionalPerformance.length > 0 && (
          <DataCard className="p-4">
            <h2 className="mb-3 text-lg font-medium text-[#f1f5f9]">Professional Performance (30d)</h2>
            <div className="space-y-3">
              {professionalPerformance.slice(0, 5).map((p) => (
                <div key={p.professional}>
                  <div className="flex items-end justify-between">
                    <span className="text-sm font-medium text-[#f1f5f9]">{p.professional}</span>
                    <span className="text-xs text-[#94a3b8]">₹{p.revenue?.toLocaleString()}</span>
                  </div>
                  <div className="mt-1 h-2 w-full overflow-hidden rounded bg-[#334155]">
                    <div
                      className="h-full bg-[#3b82f6]"
                      style={{ width: `${Math.min(100, ((p.revenue ?? 0) / (totalRevenue30d || 1)) * 100)}%` }}
                    />
                  </div>
                  <div className="mt-1 flex gap-2 text-xs text-[#94a3b8]">
                    <span>{p.completed} completed</span>
                    <span className="text-red-400">{p.canceled} canceled</span>
                  </div>
                </div>
              ))}
            </div>
          </DataCard>
        )}
        {hasStore && (
          <DataCard className="p-4">
            <h2 className="mb-3 text-lg font-medium text-[#f1f5f9]">Top Selling Products (30d)</h2>
            <div className="space-y-2">
              {topSellers.map((s) => (
                <div key={s.sku} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-[#f1f5f9]">{s.name}</p>
                    <p className="text-xs text-[#94a3b8]">SKU: {s.sku}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-[#f1f5f9]">{s.qty} units</p>
                    <p className="text-xs text-[#94a3b8]">₹{s.revenue?.toLocaleString()}</p>
                  </div>
                </div>
              ))}
              {topSellers.length === 0 && <p className="text-sm text-[#94a3b8]">No sales data</p>}
            </div>
          </DataCard>
        )}
      </div>

      {hasStore && (
        <DataCard className="mt-4 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-medium text-[#f1f5f9]">Recent orders</h2>
            <Link to="/store/orders" className="text-xs text-[#3b82f6] hover:underline">View all →</Link>
          </div>
          {actionError && (
            <div className="mb-2 rounded border border-red-500/50 bg-red-500/10 px-2 py-1.5 text-sm text-red-300">{actionError}</div>
          )}
          {recentOrders.length === 0 ? (
            <p className="text-sm text-[#94a3b8]">No orders yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[480px] text-left text-sm">
                <thead>
                  <tr className="border-b border-[#334155] text-[#94a3b8]">
                    <th className="py-2 pr-2 font-medium">Order</th>
                    <th className="py-2 pr-2 font-medium">Customer</th>
                    <th className="py-2 pr-2 font-medium">Status</th>
                    <th className="py-2 pr-2 font-medium text-right">Total</th>
                    <th className="py-2 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recentOrders.map((o) => {
                    const phone = o.customer?.phone ?? '—'
                    const canSendWhatsApp = phone && phone !== 'catalog'
                    const total = o.totals?.grand_total ?? o.totals?.subtotal ?? 0
                    const isPlaced = o.status === 'placed'
                    const isCanceled = o.status === 'canceled'
                    const busy = actionOrderId === o.id
                    return (
                      <tr key={o.id} className="border-b border-[#334155]/50">
                        <td className="py-2 pr-2 font-mono text-[#e2e8f0]">{o.id}</td>
                        <td className="py-2 pr-2 text-[#cbd5e1]">{phone}</td>
                        <td className="py-2 pr-2">
                          <span
                            className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
                              isCanceled ? 'bg-red-500/20 text-red-300' : o.status === 'confirmed' ? 'bg-green-500/20 text-green-300' : 'bg-[#334155] text-[#94a3b8]'
                            }`}
                          >
                            {o.status ?? 'placed'}
                          </span>
                        </td>
                        <td className="py-2 pr-2 text-right text-[#e2e8f0]">₹{Number(total).toLocaleString()}</td>
                        <td className="py-2">
                          <div className="flex flex-wrap gap-1">
                            {isPlaced && (
                              <button
                                type="button"
                                onClick={() => handleAcceptOrder(o.id)}
                                disabled={busy}
                                className="rounded bg-green-600 px-2 py-0.5 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50"
                              >
                                Confirm
                              </button>
                            )}
                            {!isCanceled && (
                              <button
                                type="button"
                                onClick={() => handleCancelOrder(o.id)}
                                disabled={busy}
                                className="rounded bg-red-600/80 px-2 py-0.5 text-xs font-medium text-white hover:bg-red-500 disabled:opacity-50"
                              >
                                Cancel
                              </button>
                            )}
                            {canSendWhatsApp && (
                              <button
                                type="button"
                                onClick={() => handleSendOrderWhatsApp(o.id)}
                                disabled={busy}
                                className="rounded bg-[#25D366] px-2 py-0.5 text-xs font-medium text-white hover:bg-[#20bd5a] disabled:opacity-50"
                              >
                                Send WhatsApp
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

      {hasStore && lowStock.length > 0 && (
        <DataCard className="mt-4 border-l-4 border-l-[#eab308] p-4">
          <h2 className="mb-2 text-lg font-medium text-[#fde047]">Inventory Alerts</h2>
          <div className="flex flex-wrap gap-2">
            {lowStock.map((item) => (
              <span
                key={item.sku}
                className="rounded-md border border-[#eab308]/50 bg-[#eab308]/10 px-2 py-1 text-xs text-[#fde047]"
              >
                {item.name}: {item.available_qty} left (SO in {item.days_to_stockout}d)
              </span>
            ))}
          </div>
        </DataCard>
      )}

      {/* Alerts & quick links */}
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        {noShowBlockedCount > 0 && hasService && aiNoShowEnabled && (
          <DataCard className="border border-amber-500/30 bg-amber-500/5 p-4">
            <h2 className="mb-2 text-base font-medium text-amber-200">No-Show Blocked</h2>
            <p className="text-sm text-[#94a3b8]">
              {noShowBlockedCount} phone number(s) are blocked from booking due to repeated no-shows.
            </p>
            <Link
              to="/no-show-blocked"
              className="mt-3 inline-block rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-500"
            >
              Manage blocked list
            </Link>
          </DataCard>
        )}
        {hasAI && (
          <DataCard className="p-4">
            <h2 className="mb-2 text-base font-medium text-[#f1f5f9]">AI & Predictions</h2>
            <p className="text-sm text-[#94a3b8]">View no-show risk, slot recommendations, low-stock forecast, and more.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link to="/ai" className="inline-block rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">AI Hub</Link>
              <Link to="/ai/predictions" className="inline-block rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Predictions</Link>
              <Link to="/ai/appointments" className="inline-block rounded-md border border-[#334155] px-3 py-1.5 text-sm text-[#cbd5e1] hover:bg-[#334155]">Appointments Assist</Link>
            </div>
          </DataCard>
        )}
      </div>
    </div>
  )
}
