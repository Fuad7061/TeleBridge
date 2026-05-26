import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import DialogModal from '@/components/DialogModal'

const AGENT_LABELS: Record<string, string> = {
  account: 'User Account',
  bot: 'Bot',
  account_fallback_bot: 'Account → Bot (flood fallback)',
}

const METHOD_LABELS: Record<string, string> = {
  copy: 'Copy (clean text)',
  forward: 'Forward (preserve quote)',
  forward_fallback_copy: 'Forward → Copy (fallback)',
}

const DELIVERY_COMBINED: Record<string, string> = {
  copy_account: 'Copy via account',
  copy_bot: 'Copy via bot',
  forward_account: 'Forward via account',
  forward_copy_account: 'Forward (copy if restricted)',
  copy_account_fallback_bot: 'Copy via account, flood→bot',
}

const WEBHOOK_AGENT: Record<string, string> = {
  off: 'Off',
  passthrough: 'Passthrough (Telegram + webhook)',
  destination: 'Webhook Only',
}

type Section = 'source' | 'dest' | 'delivery' | 'filters' | 'webhook' | null

interface RuleForm {
  name: string
  source_account_id: string
  source_chat_id: string
  source_chat_title: string
  dest_account_id: string
  dest_chat_id: string
  dest_chat_title: string
  delivery_agent: string
  forward_method: string
  webhook_mode: string
  webhook_url: string
  keyword_allow: string
  keyword_block: string
  media_types: string
  user_whitelist: string
  user_blacklist: string
  prefix_text: string
  cooldown_seconds: string
  schedule_from: string
  schedule_to: string
}

function emptyForm(): RuleForm {
  return {
    name: '',
    source_account_id: '',
    source_chat_id: '',
    source_chat_title: '',
    dest_account_id: '0',
    dest_chat_id: '',
    dest_chat_title: '',
    delivery_agent: 'account',
    forward_method: 'copy',
    webhook_mode: 'off',
    webhook_url: '',
    keyword_allow: '',
    keyword_block: '',
    media_types: 'all',
    user_whitelist: '',
    user_blacklist: '',
    prefix_text: '',
    cooldown_seconds: '0',
    schedule_from: '',
    schedule_to: '',
  }
}

function SectionToggle({ section, current, label, children }: { section: Section; current: Section; label: string; children: React.ReactNode }) {
  const open = current === section
  return (
    <fieldset className={`fieldset ${open ? '' : 'opacity-60'}`}>
      <button type="button" className="w-full text-left flex items-center justify-between" onClick={() => {}}>
        <legend className="cursor-pointer">{label}</legend>
        <span className="text-xs text-muted">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="mt-3 space-y-3">{children}</div>}
    </fieldset>
  )
}

function OptionBtn({ selected, label, onClick }: { selected: boolean; label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${selected ? 'bg-primary/20 border-primary text-primary' : 'border-border text-muted hover:border-primary/50'}`}>
      {label}
    </button>
  )
}

export default function RulesPage() {
  const [rules, setRules] = useState<any[]>([])
  const [logCounts, setLogCounts] = useState<Record<number, number>>({})
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [accounts, setAccounts] = useState<any[]>([])
  const [dialogs, setDialogs] = useState<any[]>([])
  const [destDialogs, setDestDialogs] = useState<any[]>([])
  const [error, setError] = useState('')
  const [expand, setExpand] = useState<Section>('source')

  const [f, setF] = useState<RuleForm>(emptyForm())

  const load = async () => {
    const [rd, ad] = await Promise.all([api.rules.list(), api.accounts.list()])
    setRules(rd.rules)
    setLogCounts(rd.log_counts || {})
    setAccounts(ad.accounts.filter((a: any) => a.status === 'connected'))
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const openNew = () => {
    setEditId(null)
    setF(emptyForm())
    setDialogs([])
    setDestDialogs([])
    setError('')
    setExpand('source')
    setShowForm(true)
  }

  const openEdit = async (rule: any) => {
    setEditId(rule.id)
    setF({
      name: rule.name,
      source_account_id: String(rule.source_account_id),
      source_chat_id: rule.source_chat_id || '',
      source_chat_title: rule.source_chat_title || '',
      dest_account_id: String(rule.dest_account_id || '0'),
      dest_chat_id: rule.dest_chat_id || '',
      dest_chat_title: rule.dest_chat_title || '',
      delivery_agent: rule.delivery_agent || 'account',
      forward_method: rule.forward_method || 'copy',
      webhook_mode: rule.webhook_mode || 'off',
      webhook_url: rule.webhook_url || '',
      keyword_allow: rule.keyword_allow || '',
      keyword_block: rule.keyword_block || '',
      media_types: rule.media_types || 'all',
      user_whitelist: rule.user_whitelist || '',
      user_blacklist: rule.user_blacklist || '',
      prefix_text: rule.prefix_text || '',
      cooldown_seconds: String(rule.cooldown_seconds || '0'),
      schedule_from: rule.schedule_from || '',
      schedule_to: rule.schedule_to || '',
    })
    setError('')
    setExpand('source')
    setShowForm(true)
    if (rule.source_account_id) {
      try { const d = await api.rules.dialogs(rule.source_account_id); setDialogs(d.dialogs) } catch { setDialogs([]) }
    }
    if (rule.dest_account_id) {
      try { const d = await api.rules.dialogs(rule.dest_account_id); setDestDialogs(d.dialogs) } catch { setDestDialogs([]) }
    }
  }

  const loadDialogs = async (accountId: string) => {
    if (!accountId || accountId === '0') { setDialogs([]); return }
    try { const d = await api.rules.dialogs(Number(accountId)); setDialogs(d.dialogs) } catch { setDialogs([]) }
  }

  const loadDestDialogs = async (accountId: string) => {
    if (!accountId || accountId === '0') { setDestDialogs([]); return }
    try { const d = await api.rules.dialogs(Number(accountId)); setDestDialogs(d.dialogs) } catch { setDestDialogs([]) }
  }

  const handleSave = async () => {
    setError('')
    const payload: Record<string, any> = {
      name: f.name,
      source_account_id: Number(f.source_account_id),
      source_chat_id: f.source_chat_id,
      source_chat_title: f.source_chat_title,
      dest_account_id: Number(f.dest_account_id),
      dest_chat_id: f.dest_chat_id,
      dest_chat_title: f.dest_chat_title,
      delivery_agent: f.delivery_agent,
      forward_method: f.forward_method,
      webhook_mode: f.webhook_mode,
      webhook_url: f.webhook_url,
      keyword_allow: f.keyword_allow,
      keyword_block: f.keyword_block,
      media_types: f.media_types,
      user_whitelist: f.user_whitelist,
      user_blacklist: f.user_blacklist,
      prefix_text: f.prefix_text,
      cooldown_seconds: Number(f.cooldown_seconds) || 0,
      schedule_from: f.schedule_from,
      schedule_to: f.schedule_to,
    }

    try {
      if (editId) await api.rules.update(editId, payload)
      else await api.rules.create(payload)
      setShowForm(false)
      await load()
    } catch (e: any) {
      if (e.errors) setError(Object.values(e.errors).join(', '))
      else setError('Failed to save')
    }
  }

  const handleToggle = async (id: number) => {
    await api.rules.toggle(id)
    await load()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this rule?')) return
    await api.rules.delete(id)
    await load()
  }

  const isWebhookOn = f.webhook_mode !== 'off'
  const hasDest = f.dest_account_id !== '0' && f.dest_chat_id

  if (loading) return <p className="text-muted">Loading...</p>

  return (
    <div>
      <div className="page-header mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Forward Rules</h2>
        <button className="btn" onClick={openNew}>+ New Rule</button>
      </div>

      {showForm && (
        <DialogModal onClose={() => setShowForm(false)}>
          <h3 className="font-semibold text-lg mb-4">{editId ? 'Edit Rule' : 'New Forward Rule'}</h3>
          {error && <div className="bg-danger/15 border border-danger/30 text-danger text-sm rounded-lg p-3 mb-4">{error}</div>}

          <div className="space-y-3 max-h-[75vh] overflow-y-auto pr-2">
            <div>
              <label className="text-xs text-muted block mb-1">Rule Name</label>
              <input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })}
                placeholder="e.g. Tech News → Announcements" />
            </div>

            <div className="flex gap-1 mb-2 flex-wrap">
              {(['source', 'dest', 'delivery', 'filters', 'webhook'] as Section[]).map((s) => (
                <button key={s} onClick={() => setExpand(s)}
                  className={`px-3 py-1 text-xs rounded-full border transition-colors ${expand === s ? 'bg-primary/20 border-primary text-primary' : 'border-border text-muted'}`}>
                  {s === 'source' ? '1. Source' : s === 'dest' ? '2. Destination' : s === 'delivery' ? '3. Delivery' : s === 'filters' ? '4. Filters' : '5. Webhook'}
                </button>
              ))}
            </div>

            {expand === 'source' && (
              <fieldset className="fieldset">
                <legend>Source</legend>
                <div className="mb-3">
                  <label className="text-xs text-muted block mb-1">Source Account</label>
                  <select className="input" value={f.source_account_id}
                    onChange={(e) => { setF({ ...f, source_account_id: e.target.value, source_chat_id: '' }); loadDialogs(e.target.value) }}>
                    <option value="">Select account...</option>
                    {accounts.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.type})</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">Source Chat</label>
                  <select className="input" value={f.source_chat_id}
                    onChange={(e) => {
                      const opt = (e.target as HTMLSelectElement).selectedOptions[0]
                      setF({ ...f, source_chat_id: e.target.value, source_chat_title: (opt as any)?.dataset?.chatTitle || '' })
                    }}>
                    <option value="">{f.source_account_id ? 'Select chat...' : 'Select account first'}</option>
                    {dialogs.map((d) => (
                      <option key={d.chat_id} value={d.chat_id} data-chat-title={d.title}>
                        {d.type === 'user' ? '👤' : d.type === 'group' ? '👥' : '📢'} {d.title}{d.username ? ` (@${d.username})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </fieldset>
            )}

            {expand === 'dest' && (
              <fieldset className="fieldset">
                <legend>Telegram Destination</legend>
                <p className="text-xs text-muted mb-3">Leave empty to use webhook-only mode</p>
                <div className="mb-3">
                  <label className="text-xs text-muted block mb-1">Destination Account</label>
                  <select className="input" value={f.dest_account_id}
                    onChange={(e) => { setF({ ...f, dest_account_id: e.target.value, dest_chat_id: '' }); loadDestDialogs(e.target.value) }}>
                    <option value="0">None (webhook only)</option>
                    {accounts.map((a) => <option key={a.id} value={a.id}>{a.name} ({a.type})</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">Destination Chat</label>
                  <select className="input" value={f.dest_chat_id}
                    onChange={(e) => {
                      const opt = (e.target as HTMLSelectElement).selectedOptions[0]
                      setF({ ...f, dest_chat_id: e.target.value, dest_chat_title: (opt as any)?.dataset?.chatTitle || '' })
                    }}>
                    <option value="">{f.dest_account_id !== '0' ? 'Select chat...' : 'Select account first'}</option>
                    {destDialogs.map((d) => (
                      <option key={d.chat_id} value={d.chat_id} data-chat-title={d.title}>
                        {d.type === 'user' ? '👤' : d.type === 'group' ? '👥' : '📢'} {d.title}{d.username ? ` (@${d.username})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </fieldset>
            )}

            {expand === 'delivery' && (
              <fieldset className="fieldset">
                <legend>Delivery</legend>

                <div className="mb-4">
                  <label className="text-xs text-muted block mb-2">Delivery Agent — who sends the message</label>
                  <div className="flex gap-2 flex-wrap">
                    <OptionBtn selected={f.delivery_agent === 'account'} label="User Account" onClick={() => setF({ ...f, delivery_agent: 'account' })} />
                    <OptionBtn selected={f.delivery_agent === 'bot'} label="Bot" onClick={() => setF({ ...f, delivery_agent: 'bot' })} />
                    <OptionBtn selected={f.delivery_agent === 'account_fallback_bot'} label="Account → Bot (flood)" onClick={() => setF({ ...f, delivery_agent: 'account_fallback_bot' })} />
                  </div>
                </div>

                <div className="mb-3">
                  <label className="text-xs text-muted block mb-2">Forwarding Method — how the message is sent</label>
                  <div className="flex gap-2 flex-wrap">
                    <OptionBtn selected={f.forward_method === 'copy'} label="Copy (clean text)" onClick={() => setF({ ...f, forward_method: 'copy' })} />
                    <OptionBtn selected={f.forward_method === 'forward'} label="Forward (preserve quote)" onClick={() => setF({ ...f, forward_method: 'forward' })} />
                    <OptionBtn selected={f.forward_method === 'forward_fallback_copy'} label="Forward → Copy" onClick={() => setF({ ...f, forward_method: 'forward_fallback_copy' })} />
                  </div>
                </div>

                <div>
                  <label className="text-xs text-muted block mb-1">Source Attribution (prefix text)</label>
                  <input className="input" value={f.prefix_text} onChange={(e) => setF({ ...f, prefix_text: e.target.value })}
                    placeholder="e.g. 📨 From Tech News:" />
                  <p className="text-xs text-muted mt-1">Prepended to every forwarded message. Leave blank for none.</p>
                </div>

                <div className="mt-3">
                  <label className="text-xs text-muted block mb-1">Deduplication Cooldown (seconds)</label>
                  <input type="number" className="input" value={f.cooldown_seconds} onChange={(e) => setF({ ...f, cooldown_seconds: e.target.value })}
                    placeholder="0 = disabled" min="0" />
                  <p className="text-xs text-muted mt-1">Skip duplicate messages within this window.</p>
                </div>
              </fieldset>
            )}

            {expand === 'filters' && (
              <fieldset className="fieldset">
                <legend>Filters</legend>

                <div className="mb-3">
                  <label className="text-xs text-muted block mb-1">Media Type Filter</label>
                  <select className="input" value={f.media_types} onChange={(e) => setF({ ...f, media_types: e.target.value })}>
                    <option value="all">All types</option>
                    <option value="text">Text only</option>
                    <option value="photo">Photos only</option>
                    <option value="text,photo">Text + Photos</option>
                    <option value="text,photo,video">Text + Photos + Videos</option>
                    <option value="photo,video,document">Media only (no text)</option>
                  </select>
                </div>

                <div className="mb-3">
                  <label className="text-xs text-muted block mb-1">Keyword Allow (comma-separated)</label>
                  <input className="input" value={f.keyword_allow} onChange={(e) => setF({ ...f, keyword_allow: e.target.value })}
                    placeholder="urgent, important, announcement" />
                  <p className="text-xs text-muted mt-1">Only forward messages containing these keywords.</p>
                </div>

                <div className="mb-3">
                  <label className="text-xs text-muted block mb-1">Keyword Block (comma-separated)</label>
                  <input className="input" value={f.keyword_block} onChange={(e) => setF({ ...f, keyword_block: e.target.value })}
                    placeholder="spam, advertise, buy now" />
                  <p className="text-xs text-muted mt-1">Skip messages containing these keywords.</p>
                </div>

                <div className="mb-3">
                  <label className="text-xs text-muted block mb-1">User Whitelist (user IDs, comma-separated)</label>
                  <input className="input" value={f.user_whitelist} onChange={(e) => setF({ ...f, user_whitelist: e.target.value })}
                    placeholder="123456, 789012" />
                  <p className="text-xs text-muted mt-1">Only forward from these users. Leave empty for all.</p>
                </div>

                <div className="mb-3">
                  <label className="text-xs text-muted block mb-1">User Blacklist (user IDs, comma-separated)</label>
                  <input className="input" value={f.user_blacklist} onChange={(e) => setF({ ...f, user_blacklist: e.target.value })}
                    placeholder="345678, 901234" />
                  <p className="text-xs text-muted mt-1">Skip messages from these users.</p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-muted block mb-1">Schedule From</label>
                    <input type="time" className="input" value={f.schedule_from} onChange={(e) => setF({ ...f, schedule_from: e.target.value })} />
                  </div>
                  <div>
                    <label className="text-xs text-muted block mb-1">Schedule To</label>
                    <input type="time" className="input" value={f.schedule_to} onChange={(e) => setF({ ...f, schedule_to: e.target.value })} />
                  </div>
                  <p className="text-xs text-muted col-span-2">Only forward messages within this time window. Leave blank for 24/7.</p>
                </div>
              </fieldset>
            )}

            {expand === 'webhook' && (
              <fieldset className="fieldset">
                <legend>Webhook</legend>

                <div className="mb-3">
                  <label className="text-xs text-muted block mb-1">Mode</label>
                  <select className="input" value={f.webhook_mode} onChange={(e) => setF({ ...f, webhook_mode: e.target.value })}>
                    <option value="off">Off</option>
                    <option value="passthrough">Passthrough (forward + webhook)</option>
                    <option value="destination">Webhook Only (no Telegram)</option>
                  </select>
                </div>

                {isWebhookOn && (
                  <div>
                    <label className="text-xs text-muted block mb-1">Webhook URL</label>
                    <input className="input" value={f.webhook_url} onChange={(e) => setF({ ...f, webhook_url: e.target.value })}
                      placeholder="https://n8n.example.com/webhook/..." />
                    <p className="text-xs text-muted mt-1">
                      n8n tip: Use <code className="text-primary">/webhook/</code> not <code className="text-primary">/webhook-test/</code>.
                      Set Webhook node to <strong>POST</strong> method.
                    </p>
                  </div>
                )}
              </fieldset>
            )}

            <div className="flex gap-2 pt-2 border-t border-border mt-4">
              <button className="btn" onClick={handleSave}>
                {editId ? 'Update Rule' : 'Create Rule'}
              </button>
              <button className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
        </DialogModal>
      )}

      <div className="card">
        <div className="card-body">
          {rules.length ? (
            <table className="table">
              <thead><tr><th>Name</th><th>Source</th><th>Destination</th><th>Delivery</th><th>Status</th><th>Forwards</th><th></th></tr></thead>
              <tbody>
                {rules.map((r) => {
                  const dl = r.delivery_agent && r.forward_method
                    ? `${AGENT_LABELS[r.delivery_agent] || r.delivery_agent} · ${METHOD_LABELS[r.forward_method] || r.forward_method}`
                    : DELIVERY_COMBINED[r.delivery_mode || ''] || r.delivery_mode || '—'
                  const hasFilters = r.keyword_allow || r.keyword_block || r.media_types !== 'all' || r.user_whitelist || r.schedule_from
                  return (
                    <tr key={r.id}>
                      <td className="font-medium">
                        <button className="text-primary hover:underline" onClick={() => openEdit(r)}>{r.name}</button>
                        {hasFilters && <span className="ml-2 text-xs text-muted" title="Has filters">⚙️</span>}
                      </td>
                      <td>
                        <div className="text-xs text-muted">{r.source_account_name || '?'}</div>
                        <span className="chat-badge">{r.source_chat_title || r.source_chat_id}</span>
                      </td>
                      <td>
                        {r.dest_chat_id ? (
                          <><div className="text-xs text-muted">{r.dest_account_name || '?'}</div><span className="chat-badge">{r.dest_chat_title || r.dest_chat_id}</span></>
                        ) : <span className="badge badge-warning">n8n only</span>}
                      </td>
                      <td><span className="badge badge-info">{dl}</span></td>
                      <td>
                        <button onClick={() => handleToggle(r.id)} className={r.is_active ? 'toggle-on' : 'toggle-off'}>
                          {r.is_active ? 'ON' : 'OFF'}
                        </button>
                      </td>
                      <td className="text-muted">{logCounts[r.id] ?? 0}</td>
                      <td className="text-right">
                        <button className="btn btn-sm btn-ghost mr-1" onClick={() => openEdit(r)}>Edit</button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(r.id)}>Del</button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <p className="text-muted text-center py-8">No forward rules yet</p>
          )}
        </div>
      </div>
    </div>
  )
}
