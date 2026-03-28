import { api, tokenStore } from './axios'

export type LoginResponse = {
  access_token: string
  token_type: string
  expires_in: number
  user?: {
    id?: string
    email?: string
    role: string
    tenant?: string
    display_name?: string
    caps?: string[]
  }
}

export type RequiresOtpResponse = {
  requires_otp: true
  session_id: string
  message: string
}

export type LoginResult = LoginResponse | RequiresOtpResponse

export function isRequiresOtp(r: LoginResult): r is RequiresOtpResponse {
  return (r as RequiresOtpResponse).requires_otp === true && !!(r as RequiresOtpResponse).session_id
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const res = await api.post<LoginResult>('/auth/login', { email, password })
  const data = res.data
  if (!isRequiresOtp(data)) {
    tokenStore.set(data.access_token)
  }
  return data
}

export async function verifyOtp(sessionId: string, otp: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/verify-otp', { session_id: sessionId, otp })
  tokenStore.set(res.data.access_token)
  return res.data
}

export async function getLoginOtpEnabled(): Promise<{ login_otp_enabled: boolean }> {
  const res = await api.get<{ login_otp_enabled: boolean }>('/auth/system/login-otp')
  return res.data
}

export async function setLoginOtpEnabled(enabled: boolean): Promise<{ login_otp_enabled: boolean }> {
  const res = await api.patch<{ login_otp_enabled: boolean }>('/auth/system/login-otp', { login_otp_enabled: enabled })
  return res.data
}

export function logout() {
  tokenStore.clear()
}
