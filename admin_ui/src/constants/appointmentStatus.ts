/**
 * Appointment status values (API/storage) and display labels for UI.
 * Use getAppointmentStatusLabel() to show user-friendly text everywhere.
 */
export const APPOINTMENT_STATUS = {
  BOOKED: 'booked',
  COMPLETED: 'completed',
  CANCELED: 'canceled',
  NEEDS_RESCHEDULE: 'needs_reschedule',
  BLOCKED: 'blocked',
  NO_SHOW: 'no_show',
} as const

export type AppointmentStatusValue = typeof APPOINTMENT_STATUS[keyof typeof APPOINTMENT_STATUS]

/** Display labels for each status (use on Appointments screen and all other pages). */
export const APPOINTMENT_STATUS_LABELS: Record<string, string> = {
  [APPOINTMENT_STATUS.BOOKED]: 'Booked',
  [APPOINTMENT_STATUS.COMPLETED]: 'Completed',
  [APPOINTMENT_STATUS.CANCELED]: 'Canceled',
  [APPOINTMENT_STATUS.NEEDS_RESCHEDULE]: 'Needs Reschedule',
  [APPOINTMENT_STATUS.BLOCKED]: 'Blocked',
  [APPOINTMENT_STATUS.NO_SHOW]: 'No show',
}

export function getAppointmentStatusLabel(status: string | undefined): string {
  if (!status) return ''
  return APPOINTMENT_STATUS_LABELS[status] ?? status
}

/** All statuses for filter dropdowns, with value and label. */
export const APPOINTMENT_STATUS_OPTIONS = [
  { value: APPOINTMENT_STATUS.BOOKED, label: APPOINTMENT_STATUS_LABELS[APPOINTMENT_STATUS.BOOKED] },
  { value: APPOINTMENT_STATUS.COMPLETED, label: APPOINTMENT_STATUS_LABELS[APPOINTMENT_STATUS.COMPLETED] },
  { value: APPOINTMENT_STATUS.NO_SHOW, label: APPOINTMENT_STATUS_LABELS[APPOINTMENT_STATUS.NO_SHOW] },
  { value: APPOINTMENT_STATUS.NEEDS_RESCHEDULE, label: APPOINTMENT_STATUS_LABELS[APPOINTMENT_STATUS.NEEDS_RESCHEDULE] },
  { value: APPOINTMENT_STATUS.BLOCKED, label: APPOINTMENT_STATUS_LABELS[APPOINTMENT_STATUS.BLOCKED] },
  { value: APPOINTMENT_STATUS.CANCELED, label: APPOINTMENT_STATUS_LABELS[APPOINTMENT_STATUS.CANCELED] },
]
