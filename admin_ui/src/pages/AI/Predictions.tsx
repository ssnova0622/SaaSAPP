import { useEffect, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Grid, Stack, Typography, Table, TableHead, TableRow, TableCell, TableBody, Chip, Tabs, Tab, TextField, MenuItem } from '@mui/material'
import ChartToolbar from '../../components/charts/ChartToolbar'
import { SERIES_COLORS } from '../../components/charts/palette'
import LineChart from '../../components/charts/LineChart'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { getTenantSettings, TenantSettings } from '@api/tenants'
import { getPredictionsSummary, getTopSellers, TopSellerItem, getSalesForecast, SalesForecastPoint, getCartRecovery, CartRecoveryResponse, getLowStockForecast, LowStockItem } from '@api/ai'

export default function PredictionsPage(){
  const { effectiveTenant: tenant, isSuper } = useEffectiveTenant()
  const [enabled, setEnabled] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string|null>(null)
  const [days, setDays] = useState<number>(30)
  const [summary, setSummary] = useState<any|null>(null)
  const [top, setTop] = useState<TopSellerItem[]>([])
  const [loadingTop, setLoadingTop] = useState<boolean>(false)
  // Tabs
  const [tab, setTab] = useState<'summary'|'top'|'forecast'|'lowstock'|'recovery'>('summary')
  // Sales forecast state
  const [horizon, setHorizon] = useState<number>(14)
  const [fcLoading, setFcLoading] = useState<boolean>(false)
  const [forecast, setForecast] = useState<SalesForecastPoint[]>([])
  const [dailyDemand, setDailyDemand] = useState<number>(0)
  const [avgUnitPrice, setAvgUnitPrice] = useState<number>(0)
  const [fcError, setFcError] = useState<string|null>(null)
  const [fcChart, setFcChart] = useState<'line'|'area'>(()=> (localStorage.getItem('ai.salesForecastChart') as any) || 'line')
  useEffect(()=>{ try{ localStorage.setItem('ai.salesForecastChart', fcChart) }catch{} }, [fcChart])
  // Cart recovery state
  const [recovery, setRecovery] = useState<CartRecoveryResponse | null>(null)
  const [recoveryLoading, setRecoveryLoading] = useState<boolean>(false)
  const [recoveryError, setRecoveryError] = useState<string|null>(null)
  const [windowHours, setWindowHours] = useState<number>(24)
  // Low-stock state
  const [lsItems, setLsItems] = useState<LowStockItem[]>([])
  const [lsLoading, setLsLoading] = useState<boolean>(false)
  const [lsError, setLsError] = useState<string|null>(null)
  const [lsLead, setLsLead] = useState<number>(3)
  const [lsSafety, setLsSafety] = useState<number>(2)
  const [prefilterOOS7, setPrefilterOOS7] = useState<boolean>(false)

  useEffect(()=>{
    (async ()=>{
      if(!tenant){ setEnabled(false); return }
      try{
        const s: TenantSettings = await getTenantSettings(tenant)
        const mods = (s.modules||[]).map(m=>String(m).toLowerCase())
        const caps = (s.capabilities||[]).map(c=>String(c).toLowerCase())
        setEnabled(mods.includes('ai') && caps.includes('ai.predictions'))
      }catch{ setEnabled(false) }
    })()
  }, [tenant])

  async function loadAll(){
    if(!tenant) return
    setLoading(true); setError(null)
    try{
      const s = await getPredictionsSummary(tenant, { days })
      setSummary(s)
    }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to load summary') }
    finally{ setLoading(false) }
    try{
      setLoadingTop(true)
      const t = await getTopSellers(tenant, { days, top: 20 })
      setTop(t.items || [])
    }catch{ /* ignore */ }
    finally{ setLoadingTop(false) }
  }

  useEffect(() => {
    if (tenant && enabled) loadAll()
  // eslint-disable-next-line
  }, [tenant, days, enabled])

  async function loadForecast(){
    if(!tenant) return
    setFcLoading(true); setFcError(null)
    try{
      const res = await getSalesForecast(tenant, { days, horizon })
      setForecast(res.items || [])
      setDailyDemand(res.daily_demand || 0)
      setAvgUnitPrice(res.avg_unit_price || 0)
    }catch(e:any){ setFcError(e?.response?.data?.detail || 'Failed to load sales forecast'); setForecast([]) }
    finally{ setFcLoading(false) }
  }

  async function loadRecovery(){
    if(!tenant) return
    setRecoveryLoading(true); setRecoveryError(null)
    try{
      const res = await getCartRecovery(tenant, { window_hours: windowHours, top: 20 })
      setRecovery(res)
    }catch(e:any){ setRecoveryError(e?.response?.data?.detail || 'Failed to load cart recovery insights'); setRecovery(null) }
    finally{ setRecoveryLoading(false) }
  }

  async function loadLowStock(){
    if(!tenant) return
    setLsLoading(true); setLsError(null)
    try{
      const res = await getLowStockForecast(tenant, { days, lead_time: lsLead, safety_days: lsSafety, top: 200 })
      setLsItems(res.items || [])
    }catch(e:any){ setLsError(e?.response?.data?.detail || 'Failed to load low‑stock forecast'); setLsItems([]) }
    finally{ setLsLoading(false) }
  }

  // Lazy load per tab (only when AI predictions enabled for tenant)
  useEffect(() => {
    if (!enabled) return
    if (tab === 'forecast') loadForecast()
    else if (tab === 'recovery') loadRecovery()
    else if (tab === 'lowstock') loadLowStock()
  // eslint-disable-next-line
  }, [tab, tenant, days, horizon, windowHours, lsLead, lsSafety, enabled])

  const disabledForTenant = !enabled && !isSuper

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems='center' justifyContent='space-between' sx={{ mb:2 }}>
        <Typography variant='h5'>AI — Predictions</Typography>
        <Stack direction='row' spacing={1} alignItems='center'>
          <Chip size='small' label={`${days} days`} />
          <Button size='small' variant={days===30?'contained':'outlined'} onClick={()=>setDays(30)}>30d</Button>
          <Button size='small' variant={days===60?'contained':'outlined'} onClick={()=>setDays(60)}>60d</Button>
          <Button size='small' variant={days===90?'contained':'outlined'} onClick={()=>setDays(90)}>90d</Button>
          <Button size='small' onClick={loadAll}>Refresh</Button>
        </Stack>
      </Stack>

      {disabledForTenant && (
        <Alert severity='info' sx={{ mb:2 }}>
          AI Predictions is disabled for this tenant. Ask Super Admin to enable it in Settings → AI Features.
        </Alert>
      )}

      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}

      {/* Tabs */}
      <Tabs value={tab} onChange={(_,v)=>setTab(v)} sx={{ mb:2 }}>
        <Tab label="Summary" value="summary" />
        <Tab label="Top sellers" value="top" />
        <Tab label="Sales forecast" value="forecast" />
        <Tab label="Low‑stock" value="lowstock" />
        <Tab label="Cart recovery" value="recovery" />
      </Tabs>

      {tab==='summary' && (
        <>
          <Grid container spacing={2} sx={{ mb:2 }}>
            <Grid item xs={12} md={3}>
              <Card onClick={()=>{ setTab('lowstock'); setPrefilterOOS7(false); }} sx={{ cursor: 'pointer' }}>
                <CardContent>
                  <Typography variant='subtitle2' color='text.secondary'>Low‑stock SKUs</Typography>
                  <Typography variant='h5'>{summary?.low_stock_count ?? (loading ? '…' : 0)}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card onClick={()=>{ setTab('lowstock'); setPrefilterOOS7(true); }} sx={{ cursor: 'pointer' }}>
                <CardContent>
                  <Typography variant='subtitle2' color='text.secondary'>Predicted OOS ≤ 7d</Typography>
                  <Typography variant='h5'>{summary?.predicted_oos_next_7d ?? (loading ? '…' : 0)}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card onClick={()=>{ setTab('recovery'); setWindowHours(24); }} sx={{ cursor: 'pointer' }}>
                <CardContent>
                  <Typography variant='subtitle2' color='text.secondary'>Abandoned carts (24h)</Typography>
                  <Typography variant='h5'>{summary?.abandoned_carts_24h ?? (loading ? '…' : 0)}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card sx={{ opacity: 0.85 }}>
                <CardContent>
                  <Typography variant='subtitle2' color='text.secondary'>Anomaly alerts</Typography>
                  <Typography variant='h5'>{summary?.anomaly_alerts ?? (loading ? '…' : 0)}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Card>
            <CardContent>
              <Stack direction='row' alignItems='center' justifyContent='space-between' sx={{ mb:1 }}>
                <Typography variant='h6'>Top sellers</Typography>
                <Button size='small' onClick={()=>loadAll()}>Refresh</Button>
              </Stack>
              <Table size='small'>
                <TableHead>
                  <TableRow>
                    <TableCell>SKU</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell align='right'>Qty</TableCell>
                    <TableCell align='right'>Revenue</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {loadingTop && (
                    <TableRow><TableCell colSpan={4}><Typography variant='body2' color='text.secondary'>Loading…</Typography></TableCell></TableRow>
                  )}
                  {!loadingTop && (!top || top.length===0) && (
                    <TableRow><TableCell colSpan={4}><Typography variant='body2' color='text.secondary'>No data</Typography></TableCell></TableRow>
                  )}
                  {!loadingTop && top.map(row => (
                    <TableRow key={row.sku}>
                      <TableCell>{row.sku}</TableCell>
                      <TableCell>{row.name}</TableCell>
                      <TableCell align='right'>{row.qty}</TableCell>
                      <TableCell align='right'>{row.revenue.toFixed ? row.revenue.toFixed(2) : row.revenue}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      {tab==='top' && (
        <Card>
          <CardContent>
            <Stack direction='row' alignItems='center' justifyContent='space-between' sx={{ mb:1 }}>
              <Typography variant='h6'>Top sellers</Typography>
              <Button size='small' onClick={()=>loadAll()}>Refresh</Button>
            </Stack>
            <Table size='small'>
              <TableHead>
                <TableRow>
                  <TableCell>SKU</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell align='right'>Qty</TableCell>
                  <TableCell align='right'>Revenue</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loadingTop && (
                  <TableRow><TableCell colSpan={4}><Typography variant='body2' color='text.secondary'>Loading…</Typography></TableCell></TableRow>
                )}
                {!loadingTop && (!top || top.length===0) && (
                  <TableRow><TableCell colSpan={4}><Typography variant='body2' color='text.secondary'>No data</Typography></TableCell></TableRow>
                )}
                {!loadingTop && top.map(row => (
                  <TableRow key={row.sku}>
                    <TableCell>{row.sku}</TableCell>
                    <TableCell>{row.name}</TableCell>
                    <TableCell align='right'>{row.qty}</TableCell>
                    <TableCell align='right'>{row.revenue.toFixed ? row.revenue.toFixed(2) : row.revenue}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {tab==='forecast' && (
        <Card>
          <CardContent>
            <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems={{ xs:'stretch', md:'center' }} justifyContent='space-between' sx={{ mb:1 }}>
              <Typography variant='h6'>Sales forecast</Typography>
              <Stack direction='row' spacing={2} alignItems='center'>
                <TextField select size='small' label='Horizon' value={horizon} onChange={e=>setHorizon(Number(e.target.value))} sx={{ minWidth: 140 }}>
                  <MenuItem value={7}>7 days</MenuItem>
                  <MenuItem value={14}>14 days</MenuItem>
                  <MenuItem value={30}>30 days</MenuItem>
                </TextField>
                <ChartToolbar
                  label='Chart'
                  options={[{value:'line',label:'Line'},{value:'area',label:'Area'}]}
                  value={fcChart}
                  onChange={(v)=>setFcChart(v as any)}
                  persistKey='ai.salesForecastChart'
                />
                <Button size='small' onClick={loadForecast}>Refresh</Button>
              </Stack>
            </Stack>
            {fcError && <Alert severity='error' sx={{ mb:1 }}>{fcError}</Alert>}
            <Typography variant='body2' color='text.secondary' sx={{ mb:1 }}>Baseline daily demand: <b>{dailyDemand}</b> • Avg unit price: <b>{avgUnitPrice}</b></Typography>
            {/* Chart */}
            {!fcLoading && forecast && forecast.length>0 ? (
              <LineChart
                data={forecast}
                xKey='date'
                yKeys={['demand_units','revenue_estimate']}
                colors={[SERIES_COLORS[0], SERIES_COLORS[2]]}
                area={fcChart==='area'}
                seriesLabels={['Demand (units)','Revenue']}
                xLabel='Date'
                yLabel='Value'
              />
            ) : (
              <Typography variant='body2' color='text.secondary'>{fcLoading ? 'Loading…' : 'No forecast'}</Typography>
            )}
            {/* Detailed table below */}
            {!fcLoading && forecast && forecast.length>0 && (
              <Table size='small' sx={{ mt: 1 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell align='right'>Demand (units)</TableCell>
                    <TableCell align='right'>Revenue</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {forecast.map((p,i)=> (
                    <TableRow key={i}>
                      <TableCell>{p.date}</TableCell>
                      <TableCell align='right'>{p.demand_units}</TableCell>
                      <TableCell align='right'>{p.revenue_estimate.toFixed ? p.revenue_estimate.toFixed(2) : p.revenue_estimate}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {tab==='lowstock' && (
        <Card>
          <CardContent>
            <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems={{ xs:'stretch', md:'center' }} justifyContent='space-between' sx={{ mb:1 }}>
              <Typography variant='h6'>Low‑stock forecast</Typography>
              <Stack direction='row' spacing={2} alignItems='center'>
                <TextField select size='small' label='Lead (days)' value={lsLead} onChange={e=>setLsLead(Number(e.target.value))} sx={{ minWidth: 140 }}>
                  <MenuItem value={0}>0</MenuItem>
                  <MenuItem value={1}>1</MenuItem>
                  <MenuItem value={2}>2</MenuItem>
                  <MenuItem value={3}>3</MenuItem>
                  <MenuItem value={5}>5</MenuItem>
                  <MenuItem value={7}>7</MenuItem>
                </TextField>
                <TextField select size='small' label='Safety (days)' value={lsSafety} onChange={e=>setLsSafety(Number(e.target.value))} sx={{ minWidth: 160 }}>
                  <MenuItem value={0}>0</MenuItem>
                  <MenuItem value={1}>1</MenuItem>
                  <MenuItem value={2}>2</MenuItem>
                  <MenuItem value={3}>3</MenuItem>
                  <MenuItem value={5}>5</MenuItem>
                </TextField>
                {prefilterOOS7 ? (
                  <Chip color='warning' label='Filter: ≤ 7 days to stockout' onDelete={()=>setPrefilterOOS7(false)} />
                ) : (
                  <Button size='small' variant='outlined' onClick={()=>setPrefilterOOS7(true)}>Show ≤ 7 days</Button>
                )}
                <Button size='small' onClick={loadLowStock}>Refresh</Button>
              </Stack>
            </Stack>
            {lsError && <Alert severity='error' sx={{ mb:1 }}>{lsError}</Alert>}
            <Table size='small'>
              <TableHead>
                <TableRow>
                  <TableCell>SKU</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell align='right'>Avail</TableCell>
                  <TableCell align='right'>Daily</TableCell>
                  <TableCell align='right'>Days to SO</TableCell>
                  <TableCell align='right'>Reorder Qty</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {lsLoading && (
                  <TableRow><TableCell colSpan={6}><Typography variant='body2' color='text.secondary'>Loading…</Typography></TableCell></TableRow>
                )}
                {!lsLoading && (!lsItems || lsItems.length===0) && (
                  <TableRow><TableCell colSpan={6}><Typography variant='body2' color='text.secondary'>No low‑stock signals yet</Typography></TableCell></TableRow>
                )}
                {!lsLoading && (prefilterOOS7 ? lsItems.filter(r => Number(r.days_to_stockout) <= 7) : lsItems).map(row => (
                  <TableRow key={row.sku}>
                    <TableCell>{row.sku}</TableCell>
                    <TableCell>{row.name}</TableCell>
                    <TableCell align='right'>{row.available_qty}</TableCell>
                    <TableCell align='right'>{row.daily_demand}</TableCell>
                    <TableCell align='right'>{row.days_to_stockout === 9999 ? '∞' : row.days_to_stockout}</TableCell>
                    <TableCell align='right'>{row.suggested_reorder_qty}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {tab==='recovery' && (
        <Card>
          <CardContent>
            <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems={{ xs:'stretch', md:'center' }} justifyContent='space-between' sx={{ mb:1 }}>
              <Typography variant='h6'>Cart recovery (last {windowHours}h)</Typography>
              <Stack direction='row' spacing={2} alignItems='center'>
                <TextField select size='small' label='Window' value={windowHours} onChange={e=>setWindowHours(Number(e.target.value))} sx={{ minWidth: 160 }}>
                  <MenuItem value={6}>6 hours</MenuItem>
                  <MenuItem value={12}>12 hours</MenuItem>
                  <MenuItem value={24}>24 hours</MenuItem>
                  <MenuItem value={48}>48 hours</MenuItem>
                  <MenuItem value={72}>72 hours</MenuItem>
                </TextField>
                <Button size='small' onClick={loadRecovery}>Refresh</Button>
              </Stack>
            </Stack>
            {recoveryError && <Alert severity='error' sx={{ mb:1 }}>{recoveryError}</Alert>}
            <Typography variant='body2' color='text.secondary' sx={{ mb:1 }}>Abandoned carts (approx): <b>{recovery?.total_abandoned ?? (recoveryLoading ? '…' : 0)}</b></Typography>
            <Table size='small'>
              <TableHead>
                <TableRow>
                  <TableCell>SKU</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell align='right'>Qty (sum in carts)</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recoveryLoading && (
                  <TableRow><TableCell colSpan={3}><Typography variant='body2' color='text.secondary'>Loading…</Typography></TableCell></TableRow>
                )}
                {!recoveryLoading && (!recovery?.top_skus || recovery.top_skus.length===0) && (
                  <TableRow><TableCell colSpan={3}><Typography variant='body2' color='text.secondary'>No data</Typography></TableCell></TableRow>
                )}
                {!recoveryLoading && (recovery?.top_skus||[]).map((r,i)=> (
                  <TableRow key={r.sku+String(i)}>
                    <TableCell>{r.sku}</TableCell>
                    <TableCell>{r.name}</TableCell>
                    <TableCell align='right'>{r.qty}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}
