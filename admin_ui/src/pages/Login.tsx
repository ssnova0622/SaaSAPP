import { useState } from 'react'
import { login, verifyOtp, isRequiresOtp } from '@api/auth'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('superadmin@example.com')
  const [password, setPassword] = useState('SuperAdmin123!@#')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [otpStep, setOtpStep] = useState(false)
  const [sessionId, setSessionId] = useState<string>('')
  const [otp, setOtp] = useState('')
  const [otpSubmitting, setOtpSubmitting] = useState(false)
  const navigate = useNavigate()
  const location = useLocation() as { state?: { from?: { pathname?: string } } }
  const { refreshUser } = useAuth()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setOtpStep(false)
    try {
      const result = await login(email, password)
      if (isRequiresOtp(result)) {
        setSessionId(result.session_id)
        setOtpStep(true)
        setOtp('')
      } else {
        refreshUser()
        const redirectTo = location.state?.from?.pathname || '/'
        navigate(redirectTo, { replace: true })
      }
    } catch (err: unknown) {
      const d = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      let msg = 'Login failed'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = (d[0] as { msg?: string })?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = (d as { msg?: string }).msg || JSON.stringify(d)
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  async function onOtpSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!sessionId || !otp.trim()) return
    setOtpSubmitting(true)
    setError(null)
    try {
      await verifyOtp(sessionId, otp.trim())
      refreshUser()
      const redirectTo = location.state?.from?.pathname || '/'
      navigate(redirectTo, { replace: true })
    } catch (err: unknown) {
      const d = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setError(typeof d === 'string' ? d : 'Invalid or expired OTP. Please try again.')
    } finally {
      setOtpSubmitting(false)
    }
  }

  if (otpStep) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0f172a] px-4">
        <div className="w-full max-w-md rounded-2xl bg-[#1e293b] border border-[#334155] p-8 shadow-xl">
          <h1 className="text-2xl font-semibold text-[#f1f5f9] text-center mb-2">Verify with OTP</h1>
          <p className="text-sm text-[#94a3b8] text-center mb-6">Enter the 6-digit code sent to your mobile number.</p>
          <form onSubmit={onOtpSubmit} className="space-y-5">
            <div>
              <label htmlFor="otp" className="block text-sm font-medium text-[#cbd5e1] mb-1.5">Verification code</label>
              <input
                id="otp"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                className="w-full rounded-lg border border-[#334155] bg-[#0f172a] text-[#f1f5f9] px-3 py-2.5 text-center text-lg tracking-widest focus:ring-2 focus:ring-[#3b82f6] focus:border-[#3b82f6] outline-none transition-shadow"
                placeholder="000000"
              />
            </div>
            {error && <p className="text-sm text-[#fca5a5]">{error}</p>}
            <button
              type="submit"
              disabled={otpSubmitting || otp.length !== 6}
              className="w-full rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white font-medium py-2.5 px-4 disabled:opacity-50 transition-colors"
            >
              {otpSubmitting ? 'Verifying…' : 'Verify and sign in'}
            </button>
            <button
              type="button"
              onClick={() => { setOtpStep(false); setError(null); setOtp(''); }}
              className="w-full text-sm text-[#94a3b8] hover:text-[#f1f5f9]"
            >
              ← Back to login
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0f172a] px-4">
      <div className="w-full max-w-md rounded-2xl bg-[#1e293b] border border-[#334155] p-8 shadow-xl">
        <h1 className="text-2xl font-semibold text-[#f1f5f9] text-center mb-2">SS Business Login</h1>
        <p className="text-sm text-[#94a3b8] text-center mb-6">Sign in to manage your tenants and settings.</p>
        <form onSubmit={onSubmit} className="space-y-5">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-[#cbd5e1] mb-1.5">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-[#334155] bg-[#0f172a] text-[#f1f5f9] px-3 py-2.5 focus:ring-2 focus:ring-[#3b82f6] focus:border-[#3b82f6] outline-none transition-shadow"
              placeholder="admin@example.com"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-[#cbd5e1] mb-1.5">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-[#334155] bg-[#0f172a] text-[#f1f5f9] px-3 py-2.5 focus:ring-2 focus:ring-[#3b82f6] focus:border-[#3b82f6] outline-none transition-shadow"
            />
          </div>
          {error && <p className="text-sm text-[#fca5a5]">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-[#3b82f6] hover:bg-[#2563eb] text-white font-medium py-2.5 px-4 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
