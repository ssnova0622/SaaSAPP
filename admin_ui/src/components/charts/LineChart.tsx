import { Stack, Typography } from '@mui/material'

export default function LineChart({
  data,
  xKey,
  yKeys,
  colors,
  area = false,
  seriesLabels = [],
  xLabel,
  yLabel,
}: {
  data: any[]
  xKey: string
  yKeys: string[]
  colors: string[]
  area?: boolean
  seriesLabels?: string[]
  xLabel?: string
  yLabel?: string
}){
  const width = 700, height = 220, pad = 32
  if (!data || !data.length) return <Typography variant="body2" color="text.secondary">No data</Typography>
  // const xs = data.map((d)=>d[xKey]) // reserved if ticks are needed later
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
    <>
      <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label="Line chart">
        <line x1={pad} y1={height-pad} x2={width-pad} y2={height-pad} stroke="#ccc" />
        <line x1={pad} y1={pad} x2={pad} y2={height-pad} stroke="#ccc" />
        {/* Axis labels */}
        {xLabel && <text x={(width)/2} y={height-4} textAnchor="middle" fill="#666" fontSize="11">{xLabel}</text>}
        {yLabel && <text x={12} y={(height)/2} transform={`rotate(-90 12 ${(height)/2})`} textAnchor="middle" fill="#666" fontSize="11">{yLabel}</text>}
        {paths}
      </svg>
      {/* Legend */}
      {seriesLabels && seriesLabels.length>0 && (
        <Stack direction="row" spacing={2} useFlexGap flexWrap="wrap" sx={{ mt: 0.5 }}>
          {seriesLabels.map((lbl, i)=> (
            <Stack key={i} direction="row" spacing={1} alignItems="center">
              <span style={{ display:'inline-block', width:12, height:12, backgroundColor: colors[i]||'#1976d2', borderRadius:2 }} />
              <Typography variant="caption" color="text.secondary">{lbl}</Typography>
            </Stack>
          ))}
        </Stack>
      )}
    </>
  )
}
