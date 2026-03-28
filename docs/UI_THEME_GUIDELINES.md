# Admin UI theme guidelines

The admin app uses a single dark theme defined in **`admin_ui/src/theme.ts`** (`appTheme`).

## Palette (use via `theme.palette` or sx)

- **Background:** default `#0f172a`, paper `#1e293b`
- **Primary:** `#3b82f6` (blue)
- **Text:** primary `#f1f5f9`, secondary `#94a3b8`
- **Borders:** `#334155` (divider)
- **Success / Warning / Error:** `#22c55e`, `#eab308`, `#ef4444`

## Do

- Use MUI components (Typography, Button, TextField, Card, Alert, etc.); they are overridden to match the theme.
- Use `sx` with theme tokens when needed, e.g. `sx={{ color: 'text.secondary' }}`, `bgcolor: 'background.paper'`, `borderColor: 'divider'`.
- Use `color="primary"`, `severity="success"` etc. on components instead of raw hex in new code.

## Avoid

- Hardcoding light-theme grays (e.g. `#e0e0e0`, `#9e9e9e`, `#eee`) in pages; use `grey` from palette or theme tokens so dark mode stays consistent.
- Inline hex for text/background unless it matches the theme palette above.

## Theme provider

`ThemeProvider` and `CssBaseline` are applied in `main.tsx`; all pages inherit the theme.
