import { useEffect, useState } from 'react'
import { listPromotions, deletePromotion, Promotion } from '@api/promotions'
import { Link, useNavigate } from 'react-router-dom'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useTenantDateFormat } from '../../hooks/useTenantDateFormat'
import { formatDateForDisplay } from '../../utils/dateFormat'
import { PageHeader } from '@components/ui/PageHeader'
import { DataCard } from '@components/ui/DataCard'
import { AppTable, AppTableHead, AppTableBody, AppTableRow, AppTh, AppTd } from '@components/ui/AppTable'
import { Button, IconButton } from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import { useAlert } from '@contexts/AlertContext'

export default function PromotionsIndex() {
  const navigate = useNavigate()
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const dateFormat = useTenantDateFormat()
  const { showConfirm } = useAlert()
  const [items, setItems] = useState<Promotion[]>([])
  const [loading, setLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  async function handleDelete(e: React.MouseEvent, p: Promotion) {
    e.stopPropagation()
    if (!tenant) return
    const ok = await showConfirm({ title: 'Delete promotion', message: `Delete promotion "${p.name}"?` })
    if (!ok) return
    setDeletingId(p.id)
    try {
      await deletePromotion(tenant, p.id)
      await load()
    } finally {
      setDeletingId(null)
    }
  }

  async function load() {
    if (!tenant) return
    const id = ++(load as unknown as { __rid: number }).__rid || (((load as unknown as { __rid: number }).__rid = 1))
    setLoading(true)
    try {
      const list = await listPromotions(tenant)
      if (id !== (load as unknown as { __rid: number }).__rid) return
      setItems(list)
    } finally {
      if (id === (load as unknown as { __rid: number }).__rid) setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [tenant])

  return (
    <div className="p-1">
      <PageHeader
        title="Promotions"
        actions={
          <div className="flex flex-wrap gap-2">
            <Button component={Link} to="/promotions/simulator" variant="outlined" sx={{ color: '#e2e8f0', borderColor: '#475569' }}>
              Simulator
            </Button>
            <Button component={Link} to="/promotions/new" variant="contained" disabled={!tenant}>
              New Promotion
            </Button>
          </div>
        }
      />
      <DataCard>
        <AppTable>
          <AppTableHead>
            <AppTableRow>
              <AppTh>Name</AppTh>
              <AppTh>Status</AppTh>
              <AppTh>Channel</AppTh>
              <AppTh>Staff (C/U)</AppTh>
              <AppTh>Created</AppTh>
              <AppTh align="right">Actions</AppTh>
            </AppTableRow>
          </AppTableHead>
          <AppTableBody>
            {items.map((p) => (
              <AppTableRow
                key={p.id}
                className="cursor-pointer hover:bg-[#334155]/50"
                onClick={() => navigate(`/promotions/${p.id}`)}
              >
                <AppTd>{p.name}</AppTd>
                <AppTd>{p.status}</AppTd>
                <AppTd>{p.channel}</AppTd>
                <AppTd>
                  <span className="block text-xs">C: {p.created_by ?? '-'}</span>
                  <span className="block text-xs">U: {p.updated_by ?? '-'}</span>
                </AppTd>
                <AppTd>{p.created_at ? formatDateForDisplay(p.created_at, dateFormat) : '-'}</AppTd>
                <AppTd align="right" onClick={e => e.stopPropagation()}>
                  <Button size="small" variant="outlined" startIcon={<EditIcon />} sx={{ color: '#e2e8f0', borderColor: '#475569' }} onClick={() => navigate(`/promotions/${p.id}`)}>Edit</Button>
                  <IconButton size="small" color="error" disabled={deletingId === p.id} onClick={e => handleDelete(e, p)} title="Delete"><DeleteIcon /></IconButton>
                </AppTd>
              </AppTableRow>
            ))}
            {items.length === 0 && (
              <AppTableRow>
                <AppTd colSpan={6} className="text-[#94a3b8]">
                  {loading ? 'Loading...' : 'No promotions'}
                </AppTd>
              </AppTableRow>
            )}
          </AppTableBody>
        </AppTable>
      </DataCard>
    </div>
  )
}
