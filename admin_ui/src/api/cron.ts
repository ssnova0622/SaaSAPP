import { api } from './axios'

export type CronJob = {
  id: string
  job_id: string
  name: string
  type: 'promotion' | 'report' | 'stock_alert' | 'retention'
  schedule_type: 'interval' | 'cron'
  schedule_value: any
  enabled: boolean
  params?: any
  last_run?: string
  next_run?: string
}

export async function listCronJobs(): Promise<CronJob[]> {
  const res = await api.get('/admin/cron-jobs')
  return res.data
}

export async function listAvailableCronActions(): Promise<Array<{job_id: string, name: string, type: string}>> {
  const res = await api.get('/admin/cron-jobs/available-actions')
  return res.data
}

export async function upsertCronJob(job: Partial<CronJob>) {
  const res = await api.post('/admin/cron-jobs', job)
  return res.data
}

export async function toggleCronJob(jobId: string, enabled: boolean) {
  const res = await api.patch(`/admin/cron-jobs/${jobId}/toggle`, null, { params: { enabled } })
  return res.data
}

export async function deleteCronJob(jobId: string) {
  const res = await api.delete(`/admin/cron-jobs/${jobId}`)
  return res.data
}

export async function runCronJob(jobId: string) {
  const res = await api.post(`/admin/cron-jobs/${jobId}/run`)
  return res.data
}
