import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function SettingsPage() {
  const [apiId, setApiId] = useState('')
  const [apiHash, setApiHash] = useState('')
  const [webhooks, setWebhooks] = useState<any[]>([])
  const [whForm, setWhForm] = useState({ name: '', url: '', secret: '' })
  const [showWhForm, setShowWhForm] = useState(false)
  const [msg, setMsg] = useState('')

  const load = async () => {
    const d = await api.settings.get()
    setApiId(d.api_id || '')
    setApiHash(d.api_hash || '')
    setWebhooks(d.webhooks || [])
  }
  useEffect(() => { load() }, [])

  const saveApi = async () => {
    await api.settings.saveApi(apiId, apiHash)
    setMsg('API config saved')
    setTimeout(() => setMsg(''), 3000)
  }

  const addWebhook = async () => {
    await api.settings.addWebhook(whForm)
    setWhForm({ name: '', url: '', secret: '' })
    setShowWhForm(false)
    await load()
  }

  const deleteWebhook = async (id: number) => {
    if (!confirm('Delete this webhook?')) return
    await api.settings.deleteWebhook(id)
    await load()
  }

  const testWebhook = async (id: number) => {
    try {
      const r = await api.settings.testWebhook(id)
      alert(r.ok ? `OK (${r.status})` : `Failed (${r.status})`)
    } catch {
      alert('Connection failed')
    }
  }

  return (
    <div>
      <div className="page-header mb-6">
        <h2 className="text-xl font-semibold">Settings</h2>
      </div>

      {msg && <div className="bg-success/15 border border-success/30 text-success text-sm rounded-lg p-3 mb-4">{msg}</div>}

      <div className="card mb-6">
        <div className="card-header"><h3 className="font-semibold">Telegram API Credentials</h3></div>
        <div className="card-body">
          <p className="text-xs text-muted mb-4">
            Required to connect user accounts. Get yours at{' '}
            <a href="https://my.telegram.org/apps" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">my.telegram.org/apps</a>
          </p>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-muted block mb-1">API ID</label>
              <input className="input" value={apiId} onChange={(e) => setApiId(e.target.value)} placeholder="123456" />
            </div>
            <div className="flex-[2]">
              <label className="text-xs text-muted block mb-1">API Hash</label>
              <input className="input" value={apiHash} onChange={(e) => setApiHash(e.target.value)} placeholder="abcdef1234567890abcdef" />
            </div>
          </div>
          <button className="btn mt-4" onClick={saveApi}>Save</button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="font-semibold">n8n Webhook Configurations</h3>
          <button className="btn btn-sm btn-ghost" onClick={() => setShowWhForm(!showWhForm)}>+ Add</button>
        </div>
        <div className="card-body">
          {showWhForm && (
            <div className="flex gap-3 mb-4 flex-wrap">
              <input className="input flex-1" placeholder="Webhook name" value={whForm.name}
                onChange={(e) => setWhForm({ ...whForm, name: e.target.value })} />
              <input className="input flex-[2]" placeholder="https://n8n.example.com/webhook/..." value={whForm.url}
                onChange={(e) => setWhForm({ ...whForm, url: e.target.value })} />
              <input className="input flex-1" placeholder="Secret (optional)" value={whForm.secret}
                onChange={(e) => setWhForm({ ...whForm, secret: e.target.value })} />
              <button className="btn btn-sm" onClick={addWebhook}>Save</button>
            </div>
          )}
          <p className="text-xs text-muted mb-4">
            n8n tip: Use <code className="text-primary">/webhook/</code> (production) not <code className="text-primary">/webhook-test/</code>.
            Set Webhook node to <strong>POST</strong> method and make the workflow Active.
          </p>

          {webhooks.length ? (
            <table className="table">
              <thead><tr><th>Name</th><th>URL</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {webhooks.map((wh) => (
                  <tr key={wh.id}>
                    <td className="font-medium">{wh.name}</td>
                    <td className="text-muted text-xs max-w-[280px] truncate">{wh.url}</td>
                    <td><span className={`inline-block w-2 h-2 rounded-full ${wh.is_active ? 'bg-success' : 'bg-muted'}`} /></td>
                    <td className="text-right">
                      <button className="btn btn-sm btn-ghost mr-1" onClick={() => testWebhook(wh.id)}>Test</button>
                      <button className="btn btn-sm btn-danger" onClick={() => deleteWebhook(wh.id)}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-muted text-center py-4">No webhooks configured</p>
          )}
        </div>
      </div>
    </div>
  )
}
