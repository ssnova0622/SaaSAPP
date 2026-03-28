### Plan: Unify chart type dropdowns, add legends (color indicators), and show X/Y axis labels

#### Goals
- The same chart type selector UX and options across all pages/tabs that show charts.
- Always show a legend (color indicators) that explains what each series/slice represents.
- Show X and Y axis labels on timeseries and bar charts.
- Keep current data APIs and behavior; purely a UI/component refactor.

---
### Scope (where this applies)
- Reports page (`admin_ui/src/pages/Reports/Index.tsx`)
  - Sales (line/area)
  - Status (horizontal/vertical bars)
  - Categories (donut/pie)
  - Customers (line/area)
- AI — Predictions page (`admin_ui/src/pages/AI/Predictions.tsx`)
  - Sales forecast tab (line/area)

Low‑stock and Cart recovery remain tables; no chart changes required there.

---
### Design overview
1) Shared Chart Toolbar
- New component `ChartToolbar` (e.g., `admin_ui/src/components/charts/ChartToolbar.tsx`).
- Props: `chartType`, `onChange`, `options: Array<{ value: string; label: string }>`, `persistKey?: string`.
- Renders a consistent MUI `TextField select` with the same size, width, and label across all pages.
- If `persistKey` is provided, writes/reads selection to/from `localStorage`.

2) Shared color palette
- New util `palette.ts` (e.g., `admin_ui/src/components/charts/palette.ts`) exporting a stable array of series colors and a category color function.
  - Example series colors: `['#1976d2', '#2e7d32', '#ed6c02', '#9c27b0', '#d32f2f']`
  - Category colors: rotate through the same set.

3) Enhanced chart primitives with labels + legends
- Move lightweight SVG charts into `admin_ui/src/components/charts/` and enhance APIs:
  - `LineChart`
    - Props: `data`, `xKey`, `yKeys`, `seriesLabels`, `colors`, `area?`, `xLabel`, `yLabel`.
    - Renders axes, series lines (or areas), a legend row (color swatches + labels), and axis labels (X at bottom center; Y rotated along left).
  - `BarChartHorizontal`
    - Props: `items`, `labelKey`, `valueKey`, `color`, `xLabel`, `yLabel`.
    - Renders bars left→right with X/Y axes baselines and labels. Optional legend (single color typically, skip by default).
  - `BarChartVertical`
    - Props: `items`, `labelKey`, `valueKey`, `color`, `xLabel`, `yLabel`.
    - Renders columns with X/Y axes and labels.
  - `DonutPieChart`
    - Props: `items`, `labelKey`, `valueKey`, `mode: 'donut'|'pie'`, `legendMax?: number`.
    - Renders donut or pie and a legend list under it mapping slice color → category label + percentage/value.
- Accessibility: add `role="img"` and `aria-label` describing the visualization.
- Responsiveness: legends wrap using MUI `Stack` with row wrap; axis labels use small font.

4) Integrate in pages
- Reports → replace per‑tab selectors with `ChartToolbar`, and swap inline charts with shared components:
  - Sales: `LineChart` with `seriesLabels=['Orders','Units','Revenue']`, `xLabel='Date'`, `yLabel='Value'`.
  - Status: `BarChartHorizontal` or `BarChartVertical` per `chartType`; labels:
    - Horizontal: `xLabel='Count'`, `yLabel='Status'`
    - Vertical: `xLabel='Status'`, `yLabel='Count'`
  - Categories: `DonutPieChart` with `mode` from selector; add legend under chart; axis labels not applicable.
  - Customers: `LineChart` with `seriesLabels=['New','Returning']`, `xLabel='Date'`, `yLabel='Customers'`.
- AI — Predictions → Sales forecast tab:
  - Add `ChartToolbar` with types `line|area` (persist key `ai.salesForecastChart`).
  - Use `LineChart` with two series: `['Demand (units)', 'Revenue']` and labels `xLabel='Date'`, `yLabel='Value'`.
  - Keep the table below for details.

5) Persisted keys (unchanged for Reports, add for AI)
- `reports.salesChart` (line|area)
- `reports.statusChart` (horizontal|vertical)
- `reports.catsChart` (donut|pie)
- `reports.custChart` (line|area)
- `ai.salesForecastChart` (line|area)

---
### Implementation steps
1) Create shared components and utils
- `admin_ui/src/components/charts/ChartToolbar.tsx`
- `admin_ui/src/components/charts/palette.ts`
- `admin_ui/src/components/charts/LineChart.tsx`
- `admin_ui/src/components/charts/BarChartHorizontal.tsx`
- `admin_ui/src/components/charts/BarChartVertical.tsx`
- `admin_ui/src/components/charts/DonutPieChart.tsx`

2) Replace in Reports tabs
- Import and use `ChartToolbar` + enhanced charts.
- Pass appropriate `seriesLabels`, `xLabel`, `yLabel`, and palette colors.

3) Replace in AI — Predictions Sales forecast
- Add toolbar + `LineChart` with 2 series; persist to `ai.salesForecastChart`.

4) QA and polish
- Verify:
  - Dropdowns look and behave the same on all tabs/pages.
  - Legends show correct labels and colors for each series/slice.
  - X and Y axis labels visible and readable; no overlap with chart.
  - Selections persist across reloads.
  - Works on small screens (legend wraps; labels shrink if needed).

5) Documentation
- Add JSDoc on components and a short README note for chart configuration under `/admin_ui/src/components/charts/`.

---
### Acceptance criteria
- All chart tabs/pages use the same chart type dropdown UX with consistent options.
- Color legends are present and correctly label each series or slice.
- X and Y axis labels appear on all timeseries and bar charts.
- No backend changes required; performance remains snappy.
- No regressions to loading/error/empty states.

---
### Timeline (estimate)
- Day 1: Build shared components (toolbar, palette, charts) with labels + legends.
- Day 2: Integrate into Reports tabs and AI Sales forecast; QA pass and polish.

If this plan looks good, I’ll proceed to implement the shared components and wire them into Reports and AI — Predictions.