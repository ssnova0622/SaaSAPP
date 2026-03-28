import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Card, CardContent, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, Tabs, Tab, Alert, Grid, Chip, MenuItem } from '@mui/material'
import { listReports, runReport, ReportDoc, downloadReportAsBlob, getSalesTimeseries, getOrdersByStatus, getCategoryMix, getCustomersTimeseries, getProfessionalPerformance, SalesPoint, StatusRow, CategoryRow, CustomersPoint, ProfessionalPerformanceRow } from '@api/reports'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useTenantDateFormat } from '../../hooks/useTenantDateFormat'
import { useAlert } from '@contexts/AlertContext'
import { formatDateForDisplay } from '../../utils/dateFormat'
import ExportMenu from '@components/ExportMenu'

// Lightweight inline SVG charts (no external deps)
function LineChart({ data, xKey, yKeys, colors, labels, area = false }: { data: any[]; xKey: string; yKeys: string[]; colors: string[]; labels?: string[]; area?: boolean }){
  const width = 700, height = 220, pad = 32
  if (!data || !data.length) return <Typography variant="body2" color="text.secondary">No data</Typography>
  const xs = data.map((d)=>d[xKey])
  const series = yKeys.map(k=> data.map((d)=> Number(d[k]||0)))
  const maxY = Math.max(1, ...series.flat())
  const stepX = (width - 2*pad) / (data.length - 1)
  const scaleY = (v:number)=> height - pad - (v / maxY) * (height - 2*pad)
  const paths = series.map((vals, si)=> {
    const lineD = vals.map((v,i)=> `${i===0?'M':'L'} ${pad + i*stepX} ${scaleY(v)}`).join(' ')
    if (area) {
      const areaD = `${lineD} L ${pad + (vals.length-1)*stepX} ${height-pad} L ${pad} ${height-pad} Z`
      return (
        <g key={si}>
          <path d={areaD} fill={(colors[si]||'#1976d2')} opacity={0.15} />
          <path d={lineD} fill="none" stroke={colors[si]||'#1976d2'} strokeWidth={2} />
        </g>
      )
    }
    return <path key={si} d={lineD} fill="none" stroke={colors[si]||'#1976d2'} strokeWidth={2} />
  })
  return (
    <Box>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="Line chart">
        <line x1={pad} y1={height-pad} x2={width-pad} y2={height-pad} stroke="#ccc" />
        <line x1={pad} y1={pad} x2={pad} y2={height-pad} stroke="#ccc" />
        {paths}
      </svg>
      {labels && (
        <Stack direction="row" spacing={2} justifyContent="center" sx={{ mt: 1 }}>
          {labels.map((l, i) => (
            <Stack key={l} direction="row" spacing={0.5} alignItems="center">
              <Box sx={{ width: 12, height: 12, bgcolor: colors[i], borderRadius: '50%' }} />
              <Typography variant="caption">{l}</Typography>
            </Stack>
          ))}
        </Stack>
      )}
    </Box>
  )
}

function BarChart({ items, labelKey, valueKey, color = '#1976d2' }: { items: any[]; labelKey: string; valueKey: string; color?: string }){
  const width = 700, barH = 18, gap = 8, pad = 16
  const h = pad + (barH + gap) * (items?.length || 0) + pad
  if (!items || !items.length) return <Typography variant="body2" color="text.secondary">No data</Typography>
  const maxV = Math.max(1, ...items.map(r=> Number(r[valueKey]||0)))
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${h}`} preserveAspectRatio="none" role="img" aria-label="Bar chart">
      {items.map((r, i)=> {
        const v = Number(r[valueKey]||0)
        const w = (v / maxV) * (width - 2*pad)
        const y = pad + i*(barH+gap)
        return (
          <g key={i}>
            <rect x={pad} y={y} width={w} height={barH} fill={color} opacity={0.85} />
            <text x={pad+4} y={y+barH-4} fill="#fff" fontSize="10">{String(r[labelKey])}</text>
            <text x={pad+w+4} y={y+barH-4} fill="#555" fontSize="10">{v}</text>
          </g>
        )
      })}
    </svg>
  )
}

function BarChartVertical({ items, labelKey, valueKey, color = '#1976d2' }: { items: any[]; labelKey: string; valueKey: string; color?: string }){
  const width = 700, height = 240, pad = 24
  if (!items || !items.length) return <Typography variant="body2" color="text.secondary">No data</Typography>
  const maxV = Math.max(1, ...items.map(r=> Number(r[valueKey]||0)))
  const stepX = (width - 2*pad) / items.length
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="Bar chart vertical">
      <line x1={pad} y1={height-pad} x2={width-pad} y2={height-pad} stroke="#ccc" />
      {items.map((r, i)=> {
        const v = Number(r[valueKey]||0)
        const barW = Math.max(8, stepX * 0.6)
        const x = pad + i*stepX + (stepX - barW)/2
        const h = (v / maxV) * (height - 2*pad)
        const y = (height - pad) - h
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={h} fill={color} opacity={0.85} />
            <text x={x + barW/2} y={height - pad + 12} textAnchor="middle" fill="#555" fontSize="10">{String(r[labelKey])}</text>
            <text x={x + barW/2} y={y - 4} textAnchor="middle" fill="#555" fontSize="10">{v}</text>
          </g>
        )
      })}
    </svg>
  )
}

function DonutChart({ items, labelKey, valueKey, pie = false }: { items: any[]; labelKey: string; valueKey: string; pie?: boolean }){
  const size = 220, r = 90, cx = size/2, cy = size/2
  const total = Math.max(1, items.reduce((s: number, it:any)=> s + Number(it[valueKey]||0), 0))
  let start = -Math.PI/2
  const arcs = items.slice(0,8).map((it:any, idx:number)=>{
    const val = Number(it[valueKey]||0)
    const ang = (val/total) * Math.PI*2
    const end = start + ang
    const large = ang > Math.PI ? 1 : 0
    const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start)
    const x2 = cx + r * Math.cos(end), y2 = cy + r * Math.sin(end)
    const path = pie
      ? `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
      : `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`
    start = end
    const color = ['#1976d2','#9c27b0','#2e7d32','#ed6c02','#d32f2f','#455a64','#6d4c41','#00897b'][idx%8]
    return <path key={idx} d={path} fill={color} opacity={0.9} />
  })
  return (
    <svg width={size} height={size} role="img" aria-label="Donut chart">
      {arcs}
      {!pie && <circle cx={cx} cy={cy} r={r*0.6} fill="#fff" />}
      {!pie && <text x={cx} y={cy} textAnchor="middle" dominantBaseline="middle" fontSize="12" fill="#555">Top categories</text>}
    </svg>
  )
}

export default function Reports(){
  const { effectiveTenant: tenant, isSuper } = useEffectiveTenant()
  const { showAlert } = useAlert()
  // Files tab (existing)
  const [files,setFiles]=useState<ReportDoc[]>([])
  const [filesLoading,setFilesLoading]=useState(false)
  // Tabs
  const [tab, setTab] = useState<'sales'|'status'|'categories'|'customers'|'performance'|'files'>('sales')
  const [days, setDays] = useState<number>(30)
  const [fromDate, setFromDate] = useState<string>('')
  const [toDate, setToDate] = useState<string>('')
  // Sales chart
  const [sales, setSales] = useState<SalesPoint[]>([])
  const [salesLoading, setSalesLoading] = useState(false)
  const [salesErr, setSalesErr] = useState<string|null>(null)
  // Status chart
  const [statusRows, setStatusRows] = useState<StatusRow[]>([])
  const [statusLoading, setStatusLoading] = useState(false)
  const [statusErr, setStatusErr] = useState<string|null>(null)
  // Category chart
  const [cats, setCats] = useState<CategoryRow[]>([])
  const [catsLoading, setCatsLoading] = useState(false)
  const [catsErr, setCatsErr] = useState<string|null>(null)
  // Customers chart
  const [cust, setCust] = useState<CustomersPoint[]>([])
  const [custLoading, setCustLoading] = useState(false)
  const [custErr, setCustErr] = useState<string|null>(null)
  // Performance chart
  const [perfRows, setPerfRows] = useState<ProfessionalPerformanceRow[]>([])
  const [perfLoading, setPerfLoading] = useState(false)
  const [perfErr, setPerfErr] = useState<string|null>(null)
  // Chart type selections (persisted in localStorage)
  const [salesChart, setSalesChart] = useState<'line'|'area'>(()=> (localStorage.getItem('reports.salesChart') as any) || 'line')
  const [statusChart, setStatusChart] = useState<'horizontal'|'vertical'>(()=> (localStorage.getItem('reports.statusChart') as any) || 'horizontal')
  const [catsChart, setCatsChart] = useState<'donut'|'pie'>(()=> (localStorage.getItem('reports.catsChart') as any) || 'donut')
  const [custChart, setCustChart] = useState<'line'|'area'>(()=> (localStorage.getItem('reports.custChart') as any) || 'line')
  const dateFormat = useTenantDateFormat()

  function formatReportDate(dateStr: string): string {
    if (!dateStr) return ''
    if (dateStr.includes('_to_')) {
      const [a, b] = dateStr.split('_to_')
      return `${formatDateForDisplay(a.trim(), dateFormat)} – ${formatDateForDisplay(b.trim(), dateFormat)}`
    }
    return formatDateForDisplay(dateStr, dateFormat)
  }

  useEffect(()=>{ localStorage.setItem('reports.salesChart', salesChart) }, [salesChart])
  useEffect(()=>{ localStorage.setItem('reports.statusChart', statusChart) }, [statusChart])
  useEffect(()=>{ localStorage.setItem('reports.catsChart', catsChart) }, [catsChart])
  useEffect(()=>{ localStorage.setItem('reports.custChart', custChart) }, [custChart])

  useEffect(() => {
    if (tab === 'files') {
      if (!fromDate) setFromDate(new Date().toISOString().slice(0, 10))
    }
  }, [tab, fromDate])

  // Loaders per tab
  async function loadFiles(){
    if(!tenant) return
    setFilesLoading(true)
    const params: any = fromDate && toDate ? { from_date: fromDate, to_date: toDate } : { }
    // If no explicit range, we can either list all or use 'days' if we want to be consistent
    // Let's use days if no range is provided to keep it uniform
    if (!fromDate && !toDate && days) {
        const today = new Date()
        const start = new Date()
        start.setDate(today.getDate() - days)
        params.from_date = start.toISOString().split('T')[0]
        params.to_date = today.toISOString().split('T')[0]
    } else if (fromDate && !toDate) {
        // If only fromDate is set, it means we want to see reports from that day onwards (or just that day)
        // User said "user can select the date based on that report will download"
        // Let's make it so if only fromDate is set, we still show a range starting from there to today
        params.from_date = fromDate
        params.to_date = new Date().toISOString().split('T')[0]
    }
    try{ const res = await listReports(tenant, { page:1, size:50, ...params }); setFiles(res.items) } finally{ setFilesLoading(false) }
  }
  async function loadSales(){
    if(!tenant) return
    setSalesLoading(true); setSalesErr(null)
    const params: any = fromDate && toDate ? { from_date: fromDate, to_date: toDate } : { days }
    try{ const res = await getSalesTimeseries(tenant, params); setSales(res.items||[]) } catch(e:any){ setSalesErr(e?.response?.data?.detail || 'Failed to load sales'); setSales([]) } finally{ setSalesLoading(false) }
  }
  async function loadStatus(){
    if(!tenant) return
    setStatusLoading(true); setStatusErr(null)
    const params: any = fromDate && toDate ? { from_date: fromDate, to_date: toDate } : { days }
    try{ const res = await getOrdersByStatus(tenant, params); setStatusRows(res.items||[]) } catch(e:any){ setStatusErr(e?.response?.data?.detail || 'Failed to load status'); setStatusRows([]) } finally{ setStatusLoading(false) }
  }
  async function loadCats(){
    if(!tenant) return
    setCatsLoading(true); setCatsErr(null)
    const params: any = fromDate && toDate ? { from_date: fromDate, to_date: toDate } : { days }
    try{ const res = await getCategoryMix(tenant, params); setCats(res.items||[]) } catch(e:any){ setCatsErr(e?.response?.data?.detail || 'Failed to load categories'); setCats([]) } finally{ setCatsLoading(false) }
  }
  async function loadCust(){
    if(!tenant) return
    setCustLoading(true); setCustErr(null)
    const params: any = fromDate && toDate ? { from_date: fromDate, to_date: toDate } : { days }
    try{ const res = await getCustomersTimeseries(tenant, params); setCust(res.items||[]) } catch(e:any){ setCustErr(e?.response?.data?.detail || 'Failed to load customers'); setCust([]) } finally{ setCustLoading(false) }
  }
  async function loadPerf(){
    if(!tenant) return
    setPerfLoading(true); setPerfErr(null)
    const params: any = fromDate && toDate ? { from_date: fromDate, to_date: toDate } : { days }
    try{ const res = await getProfessionalPerformance(tenant, params); setPerfRows(res.items||[]) } catch(e:any){ setPerfErr(e?.response?.data?.detail || 'Failed to load performance'); setPerfRows([]) } finally{ setPerfLoading(false) }
  }
  useEffect(()=>{ if(tab==='files') loadFiles(); else if(tab==='sales') loadSales(); else if(tab==='status') loadStatus(); else if(tab==='categories') loadCats(); else if(tab==='customers') loadCust(); else if(tab==='performance') loadPerf(); // eslint-disable-next-line
  }, [tenant, tab, days, fromDate, toDate])

  async function onRun(){
    if(!tenant || !fromDate) return
    await runReport(tenant, fromDate, toDate)
    await loadFiles()
  }

  async function handleDownload(date: string) {
    if (!tenant) return
    try {
      const blobUrl = await downloadReportAsBlob(tenant, date)
      window.open(blobUrl, '_blank')
    } catch (e: any) {
      console.error('Failed to download report:', e)
      showAlert(e?.response?.data?.detail || 'Failed to download report', 'error')
    }
  }

  const generateBtnLabel = useMemo(() => {
    if (!fromDate) return 'Generate'
    if (toDate && toDate !== fromDate) return `Generate for ${fromDate} to ${toDate}`
    return `Generate for ${fromDate}`
  }, [fromDate, toDate])

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems={{ xs:'flex-start', md:'center' }} justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">Reports</Typography>
        <Stack direction='row' spacing={1} alignItems='center' flexWrap='wrap'>
          <Chip size='small' label={fromDate && toDate ? `${fromDate} to ${toDate}` : `${days} days`} />
          <TextField
            type="date"
            size="small"
            label="From"
            value={fromDate}
            onChange={e => {
              setFromDate(e.target.value)
              if (!e.target.value) setDays(30)
            }}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 150 }}
          />
          <TextField
            type="date"
            size="small"
            label="To"
            value={toDate}
            onChange={e => {
              setToDate(e.target.value)
              if (!e.target.value) setDays(30)
            }}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 150 }}
          />
          {tab !== 'files' && !fromDate && !toDate && [7,14,30,60,90].map(d => (
            <Button key={d} size='small' variant={days===d?'contained':'outlined'} onClick={()=>setDays(d)}>{d}d</Button>
          ))}
          {(fromDate || toDate) && (
            <Button size='small' variant='outlined' onClick={() => { setFromDate(''); setToDate(''); setDays(30); }}>Clear Range</Button>
          )}
          <Button size='small' onClick={()=>{ if(tab==='files') loadFiles(); if(tab==='sales') loadSales(); if(tab==='status') loadStatus(); if(tab==='categories') loadCats(); if(tab==='customers') loadCust(); }}>Refresh</Button>
          {tab === 'sales' && (
            <ExportMenu
              data={sales.map((s) => ({ ...s, total_revenue: (s.total_revenue ?? 0).toFixed?.(2) ?? s.total_revenue, store_revenue: (s.store_revenue ?? 0).toFixed?.(2) ?? s.store_revenue, service_revenue: (s.service_revenue ?? 0).toFixed?.(2) ?? s.service_revenue }))}
              columns={[{ key: 'date', label: 'Date' }, { key: 'orders_count', label: 'Orders' }, { key: 'units', label: 'Units' }, { key: 'store_revenue', label: 'Store Revenue' }, { key: 'appts_count', label: 'Appointments' }, { key: 'service_revenue', label: 'Service Revenue' }, { key: 'total_revenue', label: 'Total Revenue' }]}
              filename="report_sales"
              title="Sales Report"
              size="small"
            />
          )}
          {tab === 'status' && (
            <ExportMenu
              data={statusRows}
              columns={[{ key: 'status', label: 'Status' }, { key: 'count', label: 'Count' }]}
              filename="report_orders_by_status"
              title="Orders by Status"
              size="small"
            />
          )}
          {tab === 'categories' && (
            <ExportMenu
              data={cats.map((r) => ({ category: r.category, qty: r.qty, revenue: typeof r.revenue === 'number' ? r.revenue.toFixed(2) : r.revenue, share_revenue: r.share_revenue }))}
              columns={[{ key: 'category', label: 'Category' }, { key: 'qty', label: 'Qty' }, { key: 'revenue', label: 'Revenue' }, { key: 'share_revenue', label: 'Share %' }]}
              filename="report_categories"
              title="Category Mix"
              size="small"
            />
          )}
          {tab === 'customers' && (
            <ExportMenu
              data={cust}
              columns={[{ key: 'date', label: 'Date' }, { key: 'new_customers', label: 'New Customers' }, { key: 'returning_customers', label: 'Returning Customers' }]}
              filename="report_customers"
              title="Customers Report"
              size="small"
            />
          )}
          {tab === 'performance' && (
            <ExportMenu
              data={perfRows.map((r) => ({ ...r, revenue: typeof r.revenue === 'number' ? r.revenue.toFixed(2) : r.revenue }))}
              columns={[{ key: 'professional', label: 'Professional' }, { key: 'appointments', label: 'Appointments' }, { key: 'completed', label: 'Completed' }, { key: 'revenue', label: 'Revenue' }, { key: 'canceled', label: 'Canceled' }]}
              filename="report_performance"
              title="Professional Performance"
              size="small"
            />
          )}
          {tab === 'files' && (
            <ExportMenu
              data={files.map((f) => ({ date: f.date, storage: f.storage, url_type: f.url_type, created_at: f.created_at ?? '', status: f.status ?? '' }))}
              columns={[{ key: 'date', label: 'Date' }, { key: 'storage', label: 'Storage' }, { key: 'url_type', label: 'Type' }, { key: 'created_at', label: 'Created' }, { key: 'status', label: 'Status' }]}
              filename="report_files"
              title="Generated Report Files"
              size="small"
            />
          )}
        </Stack>
      </Stack>

      <Tabs value={tab} onChange={(_,v)=>setTab(v)} sx={{ mb:2 }}>
        <Tab label="Sales" value="sales" />
        <Tab label="Status" value="status" />
        <Tab label="Categories" value="categories" />
        <Tab label="Customers" value="customers" />
        <Tab label="Performance" value="performance" />
        <Tab label="Generated Files" value="files" />
      </Tabs>

      {tab==='sales' && (
        <Card><CardContent>
          {salesErr && <Alert severity='error' sx={{ mb:1 }}>{salesErr}</Alert>}
          <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems={{ xs:'stretch', md:'center' }} justifyContent='space-between' sx={{ mb:1 }}>
            <Typography variant='subtitle1'>Revenue Overview</Typography>
            <TextField select size='small' label='Chart' value={salesChart} onChange={(e)=>setSalesChart(e.target.value as any)} sx={{ minWidth: 140 }}>
              <MenuItem value='line'>Line</MenuItem>
              <MenuItem value='area'>Area</MenuItem>
            </TextField>
          </Stack>
          {salesLoading ? (
            <Typography variant='body2' color='text.secondary'>Loading…</Typography>
          ) : (
            <LineChart
              data={sales}
              xKey='date'
              yKeys={['total_revenue', 'store_revenue', 'service_revenue']}
              colors={['#1976d2', '#2e7d32', '#ed6c02']}
              labels={['Total Revenue', 'Store Revenue', 'Service Revenue']}
              area={salesChart==='area'}
            />
          )}
        </CardContent></Card>
      )}

      {tab==='status' && (
        <Card><CardContent>
          {statusErr && <Alert severity='error' sx={{ mb:1 }}>{statusErr}</Alert>}
          <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems={{ xs:'stretch', md:'center' }} justifyContent='space-between' sx={{ mb:1 }}>
            <Typography variant='subtitle1'>Orders by status</Typography>
            <TextField select size='small' label='Layout' value={statusChart} onChange={(e)=>setStatusChart(e.target.value as any)} sx={{ minWidth: 160 }}>
              <MenuItem value='horizontal'>Horizontal bars</MenuItem>
              <MenuItem value='vertical'>Vertical bars</MenuItem>
            </TextField>
          </Stack>
          {statusLoading ? (
            <Typography variant='body2' color='text.secondary'>Loading…</Typography>
          ) : (
            (statusChart==='horizontal' ? (
              <BarChart items={statusRows} labelKey='status' valueKey='count' />
            ) : (
              <BarChartVertical items={statusRows} labelKey='status' valueKey='count' />
            ))
          )}
        </CardContent></Card>
      )}

      {tab==='categories' && (
        <Card><CardContent>
          {catsErr && <Alert severity='error' sx={{ mb:1 }}>{catsErr}</Alert>}
          <Grid container spacing={2}>
            <Grid item xs={12} md={5}>
              <Stack direction='row' spacing={2} alignItems='center' justifyContent='space-between' sx={{ mb:1 }}>
                <Typography variant='subtitle1'>Category mix</Typography>
                <TextField select size='small' label='Chart' value={catsChart} onChange={(e)=>setCatsChart(e.target.value as any)} sx={{ minWidth: 140 }}>
                  <MenuItem value='donut'>Donut</MenuItem>
                  <MenuItem value='pie'>Pie</MenuItem>
                </TextField>
              </Stack>
              {catsLoading ? (
                <Typography variant='body2' color='text.secondary'>Loading…</Typography>
              ) : (
                <DonutChart items={cats.slice(0,8)} labelKey='category' valueKey='revenue' pie={catsChart==='pie'} />
              )}
            </Grid>
            <Grid item xs={12} md={7}>
              <Table size='small'>
                <TableHead>
                  <TableRow>
                    <TableCell>Category</TableCell>
                    <TableCell align='right'>Qty</TableCell>
                    <TableCell align='right'>Revenue</TableCell>
                    <TableCell align='right'>Share %</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(!cats || cats.length===0) && !catsLoading && (
                    <TableRow><TableCell colSpan={4}><Typography variant='body2' color='text.secondary'>No data</Typography></TableCell></TableRow>
                  )}
                  {(cats||[]).map((r,i)=> (
                    <TableRow key={r.category+String(i)}>
                      <TableCell>{r.category}</TableCell>
                      <TableCell align='right'>{r.qty}</TableCell>
                      <TableCell align='right'>{r.revenue.toFixed ? r.revenue.toFixed(2) : r.revenue}</TableCell>
                      <TableCell align='right'>{r.share_revenue}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Grid>
          </Grid>
        </CardContent></Card>
      )}

      {tab==='customers' && (
        <Card><CardContent>
          {custErr && <Alert severity='error' sx={{ mb:1 }}>{custErr}</Alert>}
          <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems={{ xs:'stretch', md:'center' }} justifyContent='space-between' sx={{ mb:1 }}>
            <Typography variant='subtitle1'>New vs returning customers</Typography>
            <TextField select size='small' label='Chart' value={custChart} onChange={(e)=>setCustChart(e.target.value as any)} sx={{ minWidth: 140 }}>
              <MenuItem value='line'>Line</MenuItem>
              <MenuItem value='area'>Area</MenuItem>
            </TextField>
          </Stack>
          {custLoading ? (
            <Typography variant='body2' color='text.secondary'>Loading…</Typography>
          ) : (
            <LineChart data={cust} xKey='date' yKeys={['new_customers','returning_customers']} colors={['#1976d2','#9c27b0']} labels={['New Customers', 'Returning Customers']} area={custChart==='area'} />
          )}
        </CardContent></Card>
      )}

      {tab === 'performance' && (
        <Card><CardContent>
          {perfErr && <Alert severity='error' sx={{ mb: 1 }}>{perfErr}</Alert>}
          <Typography variant='subtitle1' sx={{ mb: 2 }}>Professional Performance</Typography>
          {perfLoading ? (
            <Typography variant='body2' color='text.secondary'>Loading…</Typography>
          ) : (
            <Table size='small'>
              <TableHead>
                <TableRow>
                  <TableCell>Professional</TableCell>
                  <TableCell align='right'>Appointments</TableCell>
                  <TableCell align='right'>Completed</TableCell>
                  <TableCell align='right'>Revenue</TableCell>
                  <TableCell align='right'>Canceled</TableCell>
                  <TableCell align='right'>Success Rate</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {perfRows.map((r, i) => (
                  <TableRow key={r.professional + i}>
                    <TableCell>{r.professional}</TableCell>
                    <TableCell align='right'>{r.appointments}</TableCell>
                    <TableCell align='right'>{r.completed}</TableCell>
                    <TableCell align='right'>₹{r.revenue.toLocaleString()}</TableCell>
                    <TableCell align='right'>{r.canceled}</TableCell>
                    <TableCell align='right'>
                      {r.appointments > 0 ? Math.round((r.completed / r.appointments) * 100) : 0}%
                    </TableCell>
                  </TableRow>
                ))}
                {!perfRows.length && (
                  <TableRow><TableCell colSpan={6} align='center'>No data available</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent></Card>
      )}

      {tab==='files' && (
        <Card>
          <CardContent>
          <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:1 }}>
            <Typography variant='subtitle1'>Generated daily and range reports</Typography>
            <Button variant="contained" onClick={onRun} disabled={!tenant || !fromDate}>{generateBtnLabel}</Button>
          </Stack>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Sent via</TableCell>
                  <TableCell>Link</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {files.map(r=> (
                  <TableRow key={r.date}>
                    <TableCell>{formatReportDate(r.date)}</TableCell>
                    <TableCell>{r.status || 'generated'}</TableCell>
                    <TableCell>{(r.sent_via||[]).join(', ')}</TableCell>
                    <TableCell>
                      {tenant ? (
                        <Button size="small" variant="text" onClick={() => handleDownload(r.date)}>Open</Button>
                      ) : '-'}
                    </TableCell>
                  </TableRow>
                ))}
                {!files.length && (
                  <TableRow><TableCell colSpan={4}><Typography variant="body2" color="text.secondary">{filesLoading? 'Loading...' : 'No reports'}</Typography></TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}
