### Plan: Show a unified chart-type dropdown with Line, Bar, Pie, and Area on all analytics tabs

#### Objectives
- Every analytics view shows the same chart-type dropdown containing: Line, Bar, Pie, Area.
- When a selected type isn’t meaningful for the dataset (e.g., Pie for time‑series), we gracefully disable it with a tooltip and auto‑fallback to a valid type.
- Keep color legend and X/Y axis labels consistent across all charts.
- Persist the user’s last selection per tab (localStorage) but validate on load and coerce to a compatible type if needed.

---

### 1) Shared chart model and toolbar (frontend)
- Create `ChartType` union: `'line' | 'area' | 'bar' | 'pie'` in `admin_ui/src/components/charts/types.ts`.
- Enhance `ChartToolbar` (existing):
  - Props: `options` → always pass 4 entries: Line, Bar, Pie, Area.
  - New props: `disabledValues?: string[]`, `help?: Record<string,string>` to show tooltips for disabled items.
  - If the controlled value is in `disabledValues`, automatically switch to the first available type and persist.

### 2) Shared chart components support all 4 options
- Line/Area: already supported by `admin_ui/src/components/charts/LineChart.tsx` (use `area` flag).
- Bar: extend or reuse `BarChartVertical` for vertical bars; for categorical sets keep `BarChartHorizontal` option.
- Pie: use/extend `DonutPieChart` to support `mode='pie'` (no inner hole). For categories and status data, show pie; for time‑series, pie will be disabled with a tooltip.
- Maintain:
  - Legend (series color → label)
  - X and Y axis labels (for Line/Area/Bar). For Pie, show a legend only.

### 3) Per‑tab compatibility rules (what’s enabled vs disabled)
- Reports → Sales (time‑series):
  - Enabled: Line, Area, Bar (vertical)
  - Disabled: Pie (tooltip: “Not applicable for time‑series”)
- Reports → Customers (time‑series):
  - Enabled: Line, Area, Bar (vertical)
  - Disabled: Pie
- Reports → Status (categorical):
  - Enabled: Bar (horizontal by default, small toggle for Vertical), Pie
  - Disabled: Line, Area (tooltip: “Not meaningful for categorical totals”)
- Reports → Categories (categorical):
  - Enabled: Bar (vertical), Pie
  - Disabled: Line, Area
- AI → Predictions → Sales forecast (time‑series):
  - Enabled: Line, Area, Bar (vertical)
  - Disabled: Pie

Note: If you prefer to force all four to render something in every tab, we can add alternate semantics (e.g., for Sales “Pie” shows overall composition Orders vs Units vs Revenue over the selected window). Default here is to disable non‑meaningful types for clarity.

### 4) Wiring in pages
- Reports tabs (Sales, Status, Categories, Customers):
  - Replace current per‑tab selectors with the unified `ChartToolbar` receiving the four options plus `disabledValues` per rules above.
  - When `value==='bar'`, choose the proper implementation:
    - Sales/Customers: `BarChartVertical` (X=Date, Y=Value)
    - Status: `BarChartHorizontal` (X=Count, Y=Status) with a small sub‑toggle for orientation if desired.
    - Categories: `BarChartVertical` (X=Category, Y=Revenue/Qty toggle in the table/controls).
  - When `value==='pie'` and tab is categorical (Status/Categories): use `DonutPieChart` in `pie` mode.
- AI → Predictions → Sales forecast:
  - Use the same `ChartToolbar` with four options; pass `disabledValues=['pie']`.

### 5) Persistence and validation
- Keep the same per‑tab keys in `localStorage` but store any of `'line'|'area'|'bar'|'pie'`.
- On mount, if persisted type is incompatible, auto‑switch to the first allowed type in this order: Line → Area → Bar → Pie, and update localStorage silently.

### 6) Legends, labels, and accessibility
- Ensure all charts:
  - Display legend using `SERIES_COLORS` for series mapping.
  - Show `xLabel` and `yLabel` for Line/Area/Bar.
  - For Pie: show legend (slice color → label) and optional percentage labels.
  - Provide `role='img'` and `aria-label` on SVGs for accessibility.

### 7) QA checklist
- Each tab shows the same dropdown with 4 entries.
- Incompatible types are disabled with a tooltip; selecting them via persisted state coerces to a valid type.
- Switching types updates the chart without re‑fetching data.
- Selections persist across reloads and tenant switches (per tab).
- Legends and axis labels remain correct across types.

### 8) Timeline
- Day 1: Implement `ChartType`, enhance `ChartToolbar`, add disabled/tooltip behavior, wire in Reports tabs.
- Day 2: Wire AI Sales forecast; add coercion logic and final QA.

### 9) Optional enhancements
- Add “stacked” option for bar charts (e.g., Sales: stack Units and Revenue normalized).
- Add a secondary selector for orientation (horizontal/vertical) when type=Bar.
- Allow switching the metric for Categories (Qty vs Revenue) for both Bar and Pie.
- CSV export for the currently visualized series/slices.

If you approve this plan, I’ll start by updating the `ChartToolbar` to show the four chart types and enforce the compatibility rules per tab, then wire it across Reports and AI — Predictions.