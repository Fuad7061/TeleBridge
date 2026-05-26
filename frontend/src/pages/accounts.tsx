import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'bot' | 'user'>('bot')
  const [form, setForm] = useState({ name: '', bot_token: '', phone: '', code: '', password: '' })
  const [error, setError] = useState('')
  const [step, setStep] = useState<'form' | 'code'>('form')

  const load = () => api.accounts.list().then((d) => setAccounts(d.accounts)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleAddBot = async () => {
    setError('')
    try {
      await api.accounts.addBot({ name: form.name, bot_token: form.bot_token })
      setForm({ name: '', bot_token: '', phone: '', code: '', password: '' })
      await load()
    } catch (e: any) { setError(e.detail || 'Failed') }
  }

  const handleSendCode = async () => {
    setError('')
    try {
      await api.accounts.sendCode({ name: form.name, phone: form.phone })
      setStep('code')
    } catch (e: any) { setError(e.detail || 'Failed') }
  }

  const handleVerify = async () => {
    setError('')
    try {
      await api.accounts.verifyCode({ code: form.code, password: form.password })
      setForm({ name: '', bot_token: '', phone: '', code: '', password: '' })
      setStep('form')
      await load()
    } catch (e: any) {
      if (e.detail === '2FA_REQUIRED') setError('2FA enabled. Enter your password below.')
      else setError(e.detail || 'Failed')
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this account?')) return
    await api.accounts.delete(id)
    await load()
  }

  if (loading) return <p className="text-muted">Loading...</p>

  return (
    <div>
      <div className="page-header mb-6">
        <h2 className="text-xl font-semibold">Accounts</h2>
      </div>

      <div className="card mb-6">
        <div className="card-header">
          <div className="flex gap-4 items-center">
            <h3 className="font-semibold">Add Account</h3>
            <div className="flex gap-2 ml-4">
              <button onClick={() => { setTab('bot'); setStep('form'); setError('') }}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${tab === 'bot' ? 'bg-primary/20 border-primary text-primary' : 'border-border text-muted'}`}>
                Bot Token
              </button>
              <button onClick={() => { setTab('user'); setStep('form'); setError('') }}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${tab === 'user' ? 'bg-primary/20 border-primary text-primary' : 'border-border text-muted'}`}>
                User Phone
              </button>
            </div>
          </div>
        </div>
        <div className="card-body">
          {error && <div className="bg-danger/15 border border-danger/30 text-danger text-sm rounded-lg p-3 mb-4">{error}</div>}

          {tab === 'bot' ? (
            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="flex-1">
                <label className="text-xs text-muted block mb-1">Name</label>
                <input className="input" placeholder="My Bot (optional)" value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="flex-[2]">
                <label className="text-xs text-muted block mb-1">Bot Token</label>
                <input className="input" placeholder="123456:ABC-DEF1234ghIkl..." value={form.bot_token}
                  onChange={(e) => setForm({ ...form, bot_token: e.target.value })} />
              </div>
              <div className="flex items-end">
                <button className="btn" onClick={handleAddBot} disabled={!form.bot_token}>Add Bot</button>
              </div>
            </div>
          ) : step === 'form' ? (
            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="flex-1">
                <label className="text-xs text-muted block mb-1">Name</label>
                <input className="input" placeholder="My Account (optional)" value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="flex-[2]">
                <label className="text-xs text-muted block mb-1">Phone Number</label>
                <input className="input" placeholder="+1234567890" value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })} />
              </div>
              <div className="flex items-end">
                <button className="btn" onClick={handleSendCode} disabled={!form.phone}>Send Code</button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row">
              <div>
                <label className="text-xs text-muted block mb-1">Verification Code</label>
                <input className="input w-32" placeholder="12345" value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })} />
              </div>
              <div className="flex-1">
                <label className="text-xs text-muted block mb-1">2FA Password (if needed)</label>
                <input className="input" placeholder="Enter 2FA password" value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })} />
              </div>
              <div className="flex items-end gap-2">
                <button className="btn" onClick={handleVerify} disabled={!form.code}>Verify</button>
                <button className="btn btn-ghost" onClick={() => { setStep('form'); setError('') }}>Back</button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header"><h3 className="font-semibold">Connected Accounts</h3></div>
        <div className="card-body">
          {accounts.length ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {accounts.map((a) => (
                <div key={a.id} className="border border-border rounded-lg p-4 hover:border-primary/40 transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <div className="font-medium text-sm">{a.name}</div>
                      <div className="text-xs text-muted">{a.type === 'bot' ? '🤖 Bot' : '👤 User'}{a.phone ? ` · ${a.phone}` : ''}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`inline-block w-2 h-2 rounded-full ${a.status === 'connected' ? 'bg-success' : 'bg-muted'}`} />
                      <button className="text-xs text-danger hover:underline" onClick={() => handleDelete(a.id)}>Remove</button>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${a.status === 'connected' ? 'bg-success/15 text-success' : 'bg-muted/15 text-muted'}`}>
                      {a.status}
                    </span>
                    {a.id && <span className="text-xs text-muted">ID: {a.id}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted text-center py-8">No accounts connected</p>
          )}
        </div>
      </div>
    </div>
  )
}
