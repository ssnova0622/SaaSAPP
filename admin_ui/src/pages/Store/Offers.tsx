import { useEffect, useMemo, useState, useRef } from 'react'
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'
import {
  listOffers,
  createOffer,
  updateOffer,
  deleteOffer,
  type Offer,
  type OfferCreatePayload,
} from '@api/offers'
import { listProducts, listProductsPublic, getProductBySku, type Product } from '@api/catalog'
import { uploadFile, fullUrlForUpload } from '@api/upload'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAlert } from '@contexts/AlertContext'

function apiErrorMessage(e: unknown, fallback: string): string {
  const d = (e as any)?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x: any) => x?.msg || JSON.stringify(x)).join(' ')
  if (d && typeof d === 'object') return (d as any).message ?? (d as any).msg ?? JSON.stringify(d)
  return (e as any)?.message || fallback
}

const defaultValidFrom = () => new Date().toISOString().slice(0, 16)
const defaultValidUntil = () => {
  const d = new Date()
  d.setMonth(d.getMonth() + 1)
  return d.toISOString().slice(0, 16)
}

export default function OffersPage() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const { showAlert, showConfirm } = useAlert()
  const [data, setData] = useState<{ items: Offer[]; total: number }>({ items: [], total: 0 })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState({
    title: '',
    description: '',
    valid_from: defaultValidFrom(),
    valid_until: defaultValidUntil(),
    product_skus: '',
    productSkusList: [] as string[],
    discount_type: 'percent' as 'percent' | 'amount',
    discount_value: '',
    brochure_url: '',
    active: true,
  })
  const [products, setProducts] = useState<Product[]>([])
  const [productsLoading, setProductsLoading] = useState(false)
  const [productsError, setProductsError] = useState<string | null>(null)
  const [brochureUploading, setBrochureUploading] = useState(false)
  const brochureFileInputRef = useRef<HTMLInputElement>(null)

  // Flat list for dropdown: base SKU + each variant SKU (name + sku), same shape as Product
  const productOptions = useMemo(() => {
    const out: Product[] = []
    for (const p of products) {
      out.push({ ...p, sku: p.sku, name: p.name || p.sku })
      const variants = (p as any).variants
      if (variants?.length) {
        for (const v of variants) {
          const variantSku = (v as any).variant_sku
          if (variantSku) out.push({ ...p, sku: variantSku, name: (p.name || p.sku) + ' — ' + variantSku })
        }
      }
    }
    return out
  }, [products])

  async function load() {
    if (!tenant) return
    const rid = ++(load as any).__rid || ((load as any).__rid = 1)
    setLoading(true)
    setError(null)
    try {
      const res = await listOffers(tenant, { page: 1, size: 100 })
      if (rid !== (load as any).__rid) return
      setData({ items: res.items, total: res.total })
    } catch (e: any) {
      if (rid === (load as any).__rid) setError(apiErrorMessage(e, 'Failed to load offers'))
    } finally {
      if (rid === (load as any).__rid) setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [tenant])

  async function loadProducts() {
    if (!tenant) return
    setProductsLoading(true)
    setProductsError(null)
    try {
      const res = await listProducts(tenant, { page: 1, size: 200 })
      setProducts(res.items || [])
    } catch (e: any) {
      try {
        const fallback = await listProductsPublic(tenant, { page: 1, size: 200 })
        setProducts(fallback.items || [])
        setProductsError(null)
      } catch (e2: any) {
        setProducts([])
        setProductsError(apiErrorMessage(e, 'Failed to load products'))
      }
    } finally {
      setProductsLoading(false)
    }
  }

  // Helpers for final price validation (product floor vs offer price)
  function computeUnitPrice(p: Product): number {
    const price = Number(p.price) || 0
    const t = (p as any).discount_type as ('amount' | 'percent' | null) | undefined
    const v = Number((p as any).discount_value || 0)
    if (t === 'amount') return Math.max(0, price - v)
    if (t === 'percent') return Math.max(0, price - (price * (v / 100)))
    return price
  }
  /** Minimum selling price (MSP) floor for offer validation; offer price must be >= this */
  function getEffectiveMsp(p: Product): number | null {
    if (p.minimum_selling_price != null && p.minimum_selling_price !== undefined) return Number(p.minimum_selling_price)
    const base = Number(p.price) || 0
    const mt = (p as any).margin_type
    const mv = Number((p as any).margin_value ?? 0)
    if (mt === 'percent') return Math.max(0, base + (base * mv / 100))
    if (mt === 'amount') return Math.max(0, base + mv)
    const mrpOrPrice = Number((p as any).mrp ?? p.price) || 0
    const t = (p as any).discount_type as ('amount' | 'percent' | null) | undefined
    const v = Number((p as any).discount_value || 0)
    if (t === 'amount') return Math.max(0, mrpOrPrice - v)
    if (t === 'percent') return Math.max(0, mrpOrPrice - (mrpOrPrice * (v / 100)))
    return mrpOrPrice
  }

  /** Base price for offer discount: use final_selling_price (Selling − Discount + VAT) when available, else computeUnitPrice */
  function getOfferBasePrice(p: Product): number {
    if (p.final_selling_price != null && p.final_selling_price !== undefined) return Number(p.final_selling_price)
    return computeUnitPrice(p)
  }

  // Load products when page mounts and when dialog opens (so dropdown has data)
  useEffect(() => {
    if (tenant) loadProducts()
  }, [tenant])

  useEffect(() => {
    if (tenant && dialogOpen && products.length === 0 && !productsLoading) loadProducts()
  }, [tenant, dialogOpen])

  function openAdd() {
    setEditId(null)
    setForm({
      title: '',
      description: '',
      valid_from: defaultValidFrom(),
      valid_until: defaultValidUntil(),
      product_skus: '',
      productSkusList: [],
      discount_type: 'percent',
      discount_value: '',
      brochure_url: '',
      active: true,
    })
    setDialogOpen(true)
  }

  function openEdit(o: Offer) {
    setEditId(o.id)
    const dt = (o.discount_info as any)?.type
    setForm({
      title: o.title,
      description: o.description || '',
      valid_from: o.valid_from ? o.valid_from.slice(0, 16) : defaultValidFrom(),
      valid_until: o.valid_until ? o.valid_until.slice(0, 16) : defaultValidUntil(),
      product_skus: (o.product_skus || []).join(', '),
      productSkusList: o.product_skus || [],
      discount_type: dt === 'amount' ? 'amount' : 'percent',
      discount_value: String((o.discount_info as any)?.value ?? ''),
      brochure_url: (o as any).brochure_url || '',
      active: o.active,
    })
    setDialogOpen(true)
  }

  async function save() {
    if (!tenant) return
    if (!form.title.trim()) {
      showAlert('Title is required', 'error')
      return
    }
    if (form.productSkusList.length === 0) {
      showAlert('Add at least one product to create an offer', 'error')
      return
    }
    if (form.productSkusList.length > 0 && (form.discount_type === 'percent' || form.discount_type === 'amount')) {
      const discountValue = parseFloat(form.discount_value) || 0
      for (const sku of form.productSkusList) {
        try {
          const prod = await getProductBySku(tenant, sku)
          if (!prod) continue
          const msp = getEffectiveMsp(prod)
          if (msp == null) continue
          const base = getOfferBasePrice(prod)
          let offerPrice = base
          if (form.discount_type === 'percent') offerPrice = Math.max(0, base - (base * discountValue / 100))
          else if (form.discount_type === 'amount') offerPrice = Math.max(0, base - discountValue)
          if (offerPrice < msp - 0.01) {
            showAlert(`Cannot save: offer price for ${prod.name || sku} (₹${offerPrice.toFixed(2)}) is below MSP (₹${msp.toFixed(2)})`, 'error')
            return
          }
        } catch {
          // allow save if product fetch fails
        }
      }
    }
    setLoading(true)
    setError(null)
    const product_skus = form.productSkusList.length ? form.productSkusList : undefined
    const discount_info =
      (form.discount_type === 'percent' || form.discount_type === 'amount') && form.discount_value
        ? { type: form.discount_type, value: parseFloat(form.discount_value) || 0 }
        : undefined
    const payload: OfferCreatePayload = {
      title: form.title.trim(),
      description: form.description.trim(),
      valid_from: form.valid_from || undefined,
      valid_until: form.valid_until || undefined,
      product_skus,
      discount_info,
      brochure_url: form.brochure_url.trim() || (editId ? '' : undefined),
      active: form.active,
    }
    try {
      if (editId) {
        await updateOffer(tenant, editId, payload)
        showAlert('Offer updated', 'success')
      } else {
        await createOffer(tenant, payload)
        showAlert('Offer added', 'success')
      }
      setDialogOpen(false)
      await load()
    } catch (e: any) {
      showAlert(apiErrorMessage(e, 'Save failed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  async function remove(o: Offer) {
    if (!tenant) return
    const ok = await showConfirm({ title: 'Delete offer', message: `Delete offer "${o.title}"?` })
    if (!ok) return
    setLoading(true)
    setError(null)
    try {
      await deleteOffer(tenant, o.id)
      showAlert('Offer deleted', 'success')
      await load()
    } catch (e: any) {
      showAlert(apiErrorMessage(e, 'Delete failed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  async function onBrochureFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !tenant) return
    e.target.value = ''
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showAlert('Please select a PDF file', 'warning')
      return
    }
    setBrochureUploading(true)
    try {
      const res = await uploadFile(tenant, file)
      const fullUrl = fullUrlForUpload(res.url)
      setForm((f) => ({ ...f, brochure_url: fullUrl }))
      showAlert('Brochure uploaded', 'success')
    } catch (err: any) {
      showAlert(apiErrorMessage(err, 'Upload failed'), 'error')
    } finally {
      setBrochureUploading(false)
    }
  }

  return (
    <Box sx={{ p: 1 }}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h5">Store — Offers</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Button variant="contained" startIcon={<AddIcon />} onClick={openAdd} disabled={!tenant}>
            Add offer
          </Button>
        </Stack>
      </Stack>

      <Alert severity="info" sx={{ mb: 2 }}>
        <Typography component="span" variant="body2">
          Add offers manually. Discount type: <strong>percentage</strong> or <strong>amount</strong>. Products are selected from your catalog. Upload a brochure PDF per offer; it is sent in WhatsApp when users view offers. Offers apply to store orders in admin when &quot;Apply offers&quot; is on.
        </Typography>
      </Alert>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{String(error)}</Alert>}

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Products</TableCell>
                <TableCell>Valid from</TableCell>
                <TableCell>Valid until</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.items.map((o) => (
                <TableRow key={o.id}>
                  <TableCell>{o.title}</TableCell>
                  <TableCell sx={{ maxWidth: 200 }}>{o.description ? `${o.description.slice(0, 60)}${o.description.length > 60 ? '…' : ''}` : '—'}</TableCell>
                  <TableCell>{o.product_skus?.length ? o.product_skus.join(', ') : '—'}</TableCell>
                  <TableCell>{o.valid_from ? new Date(o.valid_from).toLocaleDateString() : '—'}</TableCell>
                  <TableCell>{o.valid_until ? new Date(o.valid_until).toLocaleDateString() : '—'}</TableCell>
                  <TableCell>
                    <Chip size="small" label={o.active ? 'Active' : 'Inactive'} color={o.active ? 'success' : 'default'} />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => openEdit(o)} aria-label="Edit">
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => remove(o)} aria-label="Delete">
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {!data.items.length && (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography variant="body2" color="text.secondary">
                      {loading ? 'Loading…' : 'No offers. Add one.'}
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editId ? 'Edit offer' : 'Add offer'}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Title"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              fullWidth
              multiline
              minRows={2}
            />
            <TextField
              label="Valid from"
              type="datetime-local"
              value={form.valid_from}
              onChange={(e) => setForm((f) => ({ ...f, valid_from: e.target.value }))}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Valid until"
              type="datetime-local"
              value={form.valid_until}
              onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            <Autocomplete
              multiple
              options={productOptions}
              getOptionLabel={(p) => `${p.name} (${p.sku})`}
              isOptionEqualToValue={(p, v) => p.sku === (typeof v === 'string' ? v : v?.sku)}
              value={form.productSkusList.map((sku) => productOptions.find((p) => p.sku === sku)).filter(Boolean) as Product[]}
              onChange={async (_, selected) => {
                const newSkus = selected.map((p: Product) => p.sku)
                const added = newSkus.filter((s) => !form.productSkusList.includes(s))
                let validList = newSkus
                if (tenant && (form.discount_type === 'percent' || form.discount_type === 'amount') && added.length > 0) {
                  const discountValue = parseFloat(form.discount_value) || 0
                  for (const sku of added) {
                    try {
                      const prod = await getProductBySku(tenant, sku)
                      if (!prod) continue
                      const msp = getEffectiveMsp(prod)
                      if (msp == null) continue
                      const base = getOfferBasePrice(prod)
                      let offerPrice = base
                      if (form.discount_type === 'percent') offerPrice = Math.max(0, base - (base * discountValue / 100))
                      else if (form.discount_type === 'amount') offerPrice = Math.max(0, base - discountValue)
                      if (offerPrice < msp - 0.01) {
                        showAlert(`Cannot add ${prod.name || sku}: offer price ₹${offerPrice.toFixed(2)} is below product minimum ₹${msp.toFixed(2)}`, 'error')
                        validList = form.productSkusList
                        break
                      }
                    } catch {
                      // allow add if product fetch fails
                    }
                  }
                }
                setForm((f) => ({ ...f, productSkusList: validList }))
              }}
              loading={productsLoading}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Products"
                  placeholder="Select products"
                  error={!!productsError}
                  helperText={productsError}
                />
              )}
              fullWidth
            />
            <Stack direction="row" spacing={2} alignItems="flex-start">
              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Discount type</InputLabel>
                <Select
                  label="Discount type"
                  value={form.discount_type}
                  onChange={(e) => setForm((f) => ({ ...f, discount_type: e.target.value as 'percent' | 'amount' }))}
                >
                  <MenuItem value="percent">Percentage</MenuItem>
                  <MenuItem value="amount">Amount</MenuItem>
                </Select>
              </FormControl>
              <TextField
                label="Discount value"
                value={form.discount_value}
                onChange={(e) => setForm((f) => ({ ...f, discount_value: e.target.value }))}
                type="number"
                size="small"
                placeholder={form.discount_type === 'percent' ? 'e.g. 10' : 'e.g. 50'}
              />
            </Stack>
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <TextField
                label="Brochure PDF"
                value={form.brochure_url}
                onChange={(e) => setForm((f) => ({ ...f, brochure_url: e.target.value }))}
                fullWidth
                placeholder="Upload PDF or paste URL (sent in WhatsApp when users view offers)"
                size="small"
              />
              <Button
                variant="outlined"
                size="small"
                startIcon={<PictureAsPdfIcon />}
                onClick={() => brochureFileInputRef.current?.click()}
                disabled={brochureUploading || !tenant}
                sx={{ whiteSpace: 'nowrap', mt: 0.5 }}
              >
                {brochureUploading ? 'Uploading…' : 'Upload PDF'}
              </Button>
              <input
                ref={brochureFileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                style={{ display: 'none' }}
                onChange={onBrochureFileSelect}
              />
            </Stack>
            <FormControlLabel
              control={
                <Switch
                  checked={form.active}
                  onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))}
                />
              }
              label="Active"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={save} disabled={loading}>
            {loading ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
