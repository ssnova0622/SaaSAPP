import { createTheme } from '@mui/material'

/**
 * Shared dark theme for the admin app. Keeps MUI components consistent with
 * Tailwind surface/primary (slate-900, blue-500) for a single, professional SaaS look.
 */
export const appTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#3b82f6', light: '#60a5fa', dark: '#2563eb' },
    secondary: { main: '#64748b', light: '#94a3b8', dark: '#475569' },
    background: {
      default: '#0f172a',
      paper: '#1e293b',
    },
    text: {
      primary: '#f1f5f9',
      secondary: '#94a3b8',
      disabled: '#64748b',
    },
    success: { main: '#22c55e' },
    warning: { main: '#eab308' },
    error: { main: '#ef4444' },
    divider: '#334155',
  },
  typography: {
    fontFamily: '"DM Sans", "Inter", system-ui, sans-serif',
    h1: { fontSize: '1.75rem', fontWeight: 600, color: '#f1f5f9' },
    h2: { fontSize: '1.5rem', fontWeight: 600, color: '#f1f5f9' },
    h3: { fontSize: '1.25rem', fontWeight: 600, color: '#f1f5f9' },
    h4: { fontSize: '1.125rem', fontWeight: 600, color: '#f1f5f9' },
    h5: { fontSize: '1rem', fontWeight: 600, color: '#f1f5f9' },
    h6: { fontSize: '0.875rem', fontWeight: 600, color: '#f1f5f9' },
    subtitle1: { color: '#e2e8f0' },
    subtitle2: { color: '#cbd5e1', fontWeight: 600 },
    body1: { fontSize: '0.875rem', color: '#f1f5f9' },
    body2: { fontSize: '0.8125rem', color: '#e2e8f0' },
    caption: { color: '#94a3b8' },
    button: { textTransform: 'none' as const, fontWeight: 500 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiTypography: {
      styleOverrides: {
        root: {
          fontFamily: '"DM Sans", "Inter", system-ui, sans-serif',
          color: '#f1f5f9',
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: '#0f172a', color: '#f1f5f9' },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: 12,
          color: '#f1f5f9',
        },
      },
    },
    MuiCardContent: {
      styleOverrides: {
        root: { padding: 24 },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: 12,
          color: '#f1f5f9',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 8, textTransform: 'none', fontWeight: 500, color: '#f1f5f9' },
        contained: { color: '#fff' },
        containedPrimary: {
          backgroundColor: '#3b82f6',
          color: '#fff',
          '&:hover': { backgroundColor: '#2563eb', color: '#fff' },
        },
        outlined: { borderColor: '#334155', color: '#e2e8f0' },
        text: { color: '#e2e8f0' },
      },
    },
    MuiLink: {
      styleOverrides: { root: { color: '#93c5fd' } },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined' as const,
        size: 'small' as const,
      },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            backgroundColor: '#1e293b',
            borderRadius: 8,
            '& fieldset': { borderColor: '#334155' },
            '&:hover fieldset': { borderColor: '#475569' },
            '&.Mui-focused fieldset': { borderColor: '#3b82f6', borderWidth: 1.5 },
          },
          '& .MuiInputBase-input': { color: '#f1f5f9' },
          '& .MuiInputLabel-root': { color: '#94a3b8' },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderColor: '#334155',
          padding: '12px 16px',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-root': { fontWeight: 600, color: '#94a3b8' },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
    MuiAlert: {
      styleOverrides: {
        standardSuccess: { backgroundColor: 'rgba(34, 197, 94, 0.12)', color: '#86efac' },
        standardWarning: { backgroundColor: 'rgba(234, 179, 8, 0.12)', color: '#fde047' },
        standardError: { backgroundColor: 'rgba(239, 68, 68, 0.12)', color: '#fca5a5' },
        standardInfo: { backgroundColor: 'rgba(59, 130, 246, 0.12)', color: '#93c5fd' },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: 12,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#1e293b',
          borderRight: '1px solid #334155',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#0f172a',
          borderBottom: '1px solid #334155',
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: { backgroundColor: '#3b82f6' },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          color: '#94a3b8',
          '&.Mui-selected': { color: '#f1f5f9' },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        select: { color: '#f1f5f9' },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: { color: '#f1f5f9' },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: { color: '#94a3b8' },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        switchBase: {
          '&.Mui-checked': { color: '#3b82f6' },
          '&.Mui-checked + .MuiSwitch-track': { backgroundColor: '#3b82f6' },
        },
      },
    },
    MuiBox: {
      styleOverrides: {
        root: { color: 'inherit' },
      },
    },
  },
})
