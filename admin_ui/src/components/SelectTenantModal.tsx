import { useEffect, useState } from 'react'
import { listTenants } from '../api/tenants'

type SelectTenantModalProps = {
  open: boolean
  onSelect: (tenant: string) => void
}

/**
 * Modal shown to Super Admin after login when no tenant is selected.
 * Dropdown lists all tenants; on selection + Continue, page renders with that tenant's menus and data.
 * Super Admin can change tenant later via the left panel dropdown (page refreshes for new tenant).
 */
export default function SelectTenantModal({ open, onSelect }: SelectTenantModalProps) {
  const [tenants, setTenants] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<string>('')

  useEffect(() => {
    if (!open) return
    setSelected('')
    setLoading(true)
    listTenants()
      .then((list) => setTenants(list.map((t) => t.tenant)))
      .catch(() => setTenants([]))
      .finally(() => setLoading(false))
  }, [open])

  const handleContinue = () => {
    if (selected) onSelect(selected)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-xl border border-[#334155] bg-[#1e293b] shadow-xl">
        <div className="border-b border-[#334155] px-6 py-4">
          <h2 className="text-lg font-semibold text-[#f1f5f9]">Select a tenant</h2>
          <p className="mt-1 text-sm text-[#94a3b8]">
            Choose a tenant from the dropdown. The page will load with that tenant&apos;s menus and data. You can change tenant anytime using the left panel dropdown — the page will refresh for the new tenant.
          </p>
        </div>
        <div className="p-6">
          {loading ? (
            <p className="py-4 text-center text-sm text-[#94a3b8]">Loading tenants…</p>
          ) : tenants.length === 0 ? (
            <p className="py-4 text-center text-sm text-[#94a3b8]">No tenants found.</p>
          ) : (
            <>
              <label className="block text-xs font-medium text-[#94a3b8] mb-2">Tenant</label>
              <select
                value={selected}
                onChange={(e) => setSelected(e.target.value)}
                className="w-full rounded-lg border border-[#334155] bg-[#0f172a] text-[#f1f5f9] px-4 py-3 text-sm focus:ring-2 focus:ring-[#3b82f6] focus:border-[#3b82f6] outline-none"
              >
                <option value="">Select tenant…</option>
                {tenants.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  onClick={handleContinue}
                  disabled={!selected}
                  className="rounded-lg bg-[#2563eb] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#1d4ed8] disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-[#3b82f6] focus:ring-offset-2 focus:ring-offset-[#1e293b]"
                >
                  Continue
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
