import React, { createContext, useCallback, useContext, useState } from 'react'
import {
  Snackbar,
  Alert,
  AlertColor,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from '@mui/material'

export type ConfirmOptions = {
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
}

type AlertContextValue = {
  showAlert: (message: string, severity?: AlertColor) => void
  showConfirm: (options: ConfirmOptions) => Promise<boolean>
}

const defaultContext: AlertContextValue = {
  showAlert: () => {},
  showConfirm: () => Promise.resolve(false),
}

export const AlertContext = createContext<AlertContextValue>(defaultContext)

export function useAlert(): AlertContextValue {
  const ctx = useContext(AlertContext)
  return ctx ?? defaultContext
}

type SnackbarState = {
  open: boolean
  message: string
  severity: AlertColor
}

type ConfirmState = {
  open: boolean
  title: string
  message: string
  confirmLabel: string
  cancelLabel: string
  resolve: (value: boolean) => void
}

export function AlertProvider({ children }: { children: React.ReactNode }) {
  const [snackbar, setSnackbar] = useState<SnackbarState>({
    open: false,
    message: '',
    severity: 'info',
  })
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null)

  const showAlert = useCallback((message: string, severity: AlertColor = 'info') => {
    setSnackbar({ open: true, message, severity })
  }, [])

  const showConfirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    const {
      title = 'Confirm',
      message,
      confirmLabel = 'OK',
      cancelLabel = 'Cancel',
    } = options
    return new Promise<boolean>((resolve) => {
      setConfirmState({
        open: true,
        title,
        message,
        confirmLabel,
        cancelLabel,
        resolve,
      })
    })
  }, [])

  const handleConfirmClose = useCallback((confirmed: boolean) => {
    setConfirmState((prev) => {
      if (prev) prev.resolve(confirmed)
      return null
    })
  }, [])

  return (
    <AlertContext.Provider value={{ showAlert, showConfirm }}>
      {children}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
      <Dialog
        open={!!confirmState}
        onClose={() => handleConfirmClose(false)}
        PaperProps={{
          sx: {
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
          },
        }}
      >
        {confirmState && (
          <>
            <DialogTitle sx={{ color: 'text.primary', fontWeight: 600, fontSize: '1.25rem' }}>
              {confirmState.title}
            </DialogTitle>
            <DialogContent>
              <DialogContentText sx={{ color: 'text.secondary', fontSize: '1rem' }}>
                {confirmState.message}
              </DialogContentText>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2, pt: 0 }}>
              <Button onClick={() => handleConfirmClose(false)} color="inherit">
                {confirmState.cancelLabel}
              </Button>
              <Button
                variant="contained"
                onClick={() => handleConfirmClose(true)}
                color="primary"
              >
                {confirmState.confirmLabel}
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </AlertContext.Provider>
  )
}
