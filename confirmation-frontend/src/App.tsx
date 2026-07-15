import { useState, useEffect } from 'react'
import './App.css'

interface TokenInfo {
  valid: boolean
  used: boolean
  team_id: number
  team_name: string
  captain_ign: string
  email_confirmed: boolean
  expires_at: number
  is_expired: boolean
}

function App() {
  const [token, setToken] = useState<string | null>(null)
  const [apiHost, setApiHost] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [confirmSuccess, setConfirmSuccess] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)
  const [timeLeft, setTimeLeft] = useState<string>('Calculating...')

  // Parse token and api from query string
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const t = params.get('token')
    const api = params.get('api')
    setToken(t)
    setApiHost(api)
  }, [])

  // Fetch token info once token and api host are known
  useEffect(() => {
    if (!apiHost || !token) {
      if (token && !apiHost) {
        setError('Missing api query parameter.')
        setLoading(false)
      } else if (!token && apiHost) {
        setError('Missing token query parameter.')
        setLoading(false)
      } else {
        // Both null (e.g. landing page)
        setLoading(false)
      }
      return
    }

    const fetchTokenInfo = async () => {
      try {
        setLoading(true)
        const response = await fetch(`${apiHost}/api/token-info/${token}`)
        if (!response.ok) {
          if (response.status === 404) {
            setError('Invalid Activation Link')
          } else {
            const data = await response.json().catch(() => ({}))
            setError(data.detail || 'Could not verify token.')
          }
          return
        }
        const data = await response.json()
        setTokenInfo(data)
      } catch (err: any) {
        setError(`Cannot reach API server: ${err.message}`)
      } finally {
        setLoading(false)
      }
    }

    fetchTokenInfo()
  }, [token, apiHost])

  // Countdown timer logic
  useEffect(() => {
    if (!tokenInfo || tokenInfo.used || tokenInfo.is_expired) return

    const targetTime = tokenInfo.expires_at * 1000

    const updateTimer = () => {
      const now = new Date().getTime()
      const diff = targetTime - now

      if (diff <= 0) {
        setTimeLeft('Expired')
        setTokenInfo((prev) => prev ? { ...prev, is_expired: true } : null)
        return
      }

      const mins = Math.floor(diff / 60000)
      const secs = Math.floor((diff % 60000) / 1000)
      setTimeLeft(`${mins}m ${secs}s`)
    }

    const timer = setInterval(updateTimer, 1000)
    updateTimer()

    return () => clearInterval(timer)
  }, [tokenInfo])

  const handleConfirm = async () => {
    if (!token || !apiHost) return
    setActionLoading(true)
    try {
      const response = await fetch(`${apiHost}/api/confirm/${token}`, {
        method: 'POST',
      })
      if (response.ok) {
        setConfirmSuccess(true)
      } else {
        const data = await response.json().catch(() => ({}))
        alert(`Error: ${data.detail || 'Could not confirm registration.'}`)
      }
    } catch (err: any) {
      alert(`Network error: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  const handleResend = async () => {
    if (!token || !apiHost) return
    setActionLoading(true)
    try {
      const response = await fetch(`${apiHost}/api/resend/${token}`, {
        method: 'POST',
      })
      if (response.ok) {
        setResendSuccess(true)
      } else {
        const data = await response.json().catch(() => ({}))
        alert(`Error: ${data.detail || 'Could not request new link.'}`)
      }
    } catch (err: any) {
      alert(`Network error: ${err.message}`)
    } finally {
      setActionLoading(false)
    }
  }

  // ── Render States ──────────────────────────────────────────────────────────

  const renderCardContent = () => {
    if (loading) {
      return (
        <div className="text-center py-6">
          <div className="w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-zinc-400 text-sm">Verifying registration details...</p>
        </div>
      )
    }

    if (error || !token || !apiHost) {
      return (
        <div className="text-center">
          <h2 className="font-display text-2xl font-bold text-red-500 mb-4">
            {error || 'Invalid Registration Link'}
          </h2>
          <p className="text-zinc-400 text-sm mb-6">
            Please check that the link you clicked matches the one in your confirmation email, or contact a moderator.
          </p>
          <div className="h-px bg-zinc-800 my-6"></div>
          <p className="text-xs text-zinc-600">Verification Link Error</p>
        </div>
      )
    }

    if (confirmSuccess) {
      return (
        <div className="text-center">
          <h2 className="font-display text-2xl font-bold text-emerald-500 mb-4">
            Registration Confirmed
          </h2>
          <p className="text-zinc-400 text-sm mb-6">
            Roster provisioned successfully for team <strong>{tokenInfo?.team_name}</strong>. You are authorized to begin the roster finalization phase on Discord.
          </p>
          <div className="h-px bg-zinc-800 my-6"></div>
          <p className="text-xs text-emerald-600 font-semibold font-display tracking-widest uppercase">
            Success
          </p>
        </div>
      )
    }

    if (resendSuccess) {
      return (
        <div className="text-center">
          <h2 className="font-display text-2xl font-bold text-emerald-500 mb-4">
            New Token Sent
          </h2>
          <p className="text-zinc-400 text-sm mb-6">
            A new activation link has been sent to your registered captain email address. Please check your Gmail (including spam folders).
          </p>
          <div className="h-px bg-zinc-800 my-6"></div>
          <p className="text-xs text-emerald-600 font-semibold font-display tracking-widest uppercase">
            Sent
          </p>
        </div>
      )
    }

    if (tokenInfo?.used) {
      return (
        <div className="text-center">
          <h2 className="font-display text-2xl font-bold text-emerald-500 mb-4">
            Already Confirmed
          </h2>
          <p className="text-zinc-400 text-sm mb-6">
            The team <strong>{tokenInfo.team_name}</strong> has already been confirmed. You are ready for the tournament!
          </p>
          <div className="h-px bg-zinc-800 my-6"></div>
          <p className="text-xs text-emerald-600 font-semibold font-display tracking-widest uppercase">
            Verified
          </p>
        </div>
      )
    }

    if (tokenInfo?.is_expired) {
      return (
        <div className="text-center">
          <h2 className="font-display text-2xl font-bold text-red-500 mb-4">
            Activation Link Expired
          </h2>
          <p className="text-zinc-400 text-sm mb-6">
            Verification links expire after 1 hour. Request a new token below to continue.
          </p>
          <button
            onClick={handleResend}
            disabled={actionLoading}
            className="w-full bg-red-500 hover:bg-red-600 disabled:bg-red-750 text-white font-display text-xs font-bold tracking-widest uppercase py-3 transition-colors cursor-pointer"
          >
            {actionLoading ? 'Processing...' : 'Request New Activation Token'}
          </button>
          <div className="h-px bg-zinc-800 my-6"></div>
          <p className="text-xs text-zinc-600">Token Expired</p>
        </div>
      )
    }

    // Default: Pending confirmation
    return (
      <div className="text-center">
        <h2 className="font-display text-2xl font-bold text-white mb-2">
          Roster Provisioning
        </h2>
        <p className="text-zinc-400 text-sm mb-6">
          Confirm registration for team:{' '}
          <strong className="text-red-500">{tokenInfo?.team_name}</strong>
        </p>

        <div className="bg-zinc-950 p-4 border border-zinc-800 text-left mb-6 text-sm flex flex-col gap-2 rounded-none">
          <div>
            <span className="text-zinc-500">Captain IGN:</span>{' '}
            {tokenInfo?.captain_ign}
          </div>
          <div>
            <span className="text-zinc-500">Expires in:</span>{' '}
            <span className="text-red-400 font-mono font-semibold">{timeLeft}</span>
          </div>
        </div>

        <button
          onClick={handleConfirm}
          disabled={actionLoading}
          className="w-full bg-red-500 hover:bg-red-600 disabled:bg-red-750 text-white font-display text-xs font-bold tracking-widest uppercase py-3 transition-colors cursor-pointer"
        >
          {actionLoading ? 'Confirming...' : 'Confirm Registration'}
        </button>

        <div className="h-px bg-zinc-800 my-6"></div>
        <p className="text-xs text-zinc-600">Pending Verification</p>
      </div>
    )
  }

  return (
    <div className="bg-zinc-950 text-white min-h-screen flex flex-col justify-between">
      {/* Header */}
      <header className="bg-zinc-900 border-b border-zinc-800 py-4 px-6 w-full">
        <div className="max-w-4xl mx-auto flex justify-between items-center">
          <h1 className="font-display text-sm tracking-[0.2em] text-red-500 font-extrabold uppercase">
            VALORANT TOURNAMENT SERIES
          </h1>
        </div>
      </header>

      {/* Main content wrapper */}
      <main className="flex-grow flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 p-8 shadow-2xl relative overflow-hidden rounded-none">
          {/* Red accent top bar */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-red-500"></div>
          {renderCardContent()}
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-zinc-900 border-t border-zinc-800 py-6 text-center text-xs text-zinc-500 w-full">
        <div className="max-w-4xl mx-auto">
          <p className="font-display tracking-widest text-zinc-400 font-bold uppercase mb-2">
            VALORANT TOURNAMENT SERIES
          </p>
          <p>© 2026 VALORANT TOURNAMENT SERIES. ALL RIGHTS RESERVED.</p>
        </div>
      </footer>
    </div>
  )
}

export default App
