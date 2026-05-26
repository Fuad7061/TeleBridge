import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

const MEDIA_ICON: Record<string, string> = {
  photo: '🖼️',
  video: '🎥',
  document: '📄',
  audio: '🎵',
  other: '📎',
}

function MsgCell({ text, media }: { text: string; media: string }) {
  const [open, setOpen] = useState(false)
  const preview = text ? text.slice(0, 80) : ''
  const hasMore = text.length > 80
  if (!text && !media) return <span className="text-muted text-xs">—</span>
  return (
    <div className="max-w-xs">
      <div className="flex items-start gap-1">
        {media && <span title={media}>{MEDIA_ICON[media] || '📎'}</span>}
        {text ? (
          <span className="text-xs cursor-pointer" onClick={() => setOpen(!open)}>
            {open ? text : hasMore ? `${preview}...` : preview}
          </span>
        ) : (
          <span className="text-xs italic text-muted">[media only]</span>
        )}
      </div>
      {hasMore && (
        <button className="text-xs text-primary hover:underline mt-0.5" onClick={() => setOpen(!open)}>
          {open ? '▲ less' : '▼ more'}
        </button>
      )}
    </div>
  )
}

const STATUS_BADGE: Record<string, string> = {
  success: 'badge badge-success',
  error: 'badge badge-danger',
}

export default function LogsPage() {
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('')

  const load = () => api.logs.list({ limit: 100 }).then((d) => setLogs(d.logs)).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  const handleClear = async () => {
    if (!confirm('Clear all logs?')) return
    await api.logs.clear()
    setLogs([])
  }

  const filtered = filter ? logs.filter((l) => l.status === filter) : logs

  if (loading) return <p className="text-muted">Loading...</p>

  return (
    <div>
      <div className="page-header mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Forward Logs</h2>
        {logs.length > 0 && <button className="btn btn-sm btn-danger" onClick={handleClear}>Clear All</button>}
      </div>

      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-sm">Activity Log</h3>
            <div className="flex gap-1">
              {['', 'success', 'error'].map((s) => (
                <button key={s} onClick={() => setFilter(s)}
                  className={`px-2 py-0.5 text-xs rounded-full border transition-colors ${filter === s ? 'bg-primary/20 border-primary text-primary' : 'border-border text-muted'}`}>
                  {s || 'All'}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="card-body">
          {filtered.length ? (
            <div className="overflow-x-auto">
              <table className="table">
                <thead>
                  <tr><th>Rule</th><th>Source</th><th>Msg ID</th><th>Message</th><th>Status</th><th>Dest</th><th>Latency</th><th>Error</th><th>Time</th></tr>
                </thead>
                <tbody>
                  {filtered.map((log) => (
                    <tr key={log.id} className={log.status === 'error' ? 'bg-danger/5' : ''}>
                      <td className="text-primary text-xs font-medium whitespace-nowrap">{log.rule_name}</td>
                      <td className="text-muted text-xs max-w-[100px] truncate" title={log.source_chat_title}>{log.source_chat_title || '—'}</td>
                      <td className="text-muted text-xs">{log.source_msg_id || '—'}</td>
                      <td><MsgCell text={log.message_text || ''} media={log.message_media_type || ''} /></td>
                      <td><span className={STATUS_BADGE[log.status] || 'badge'}>{log.status}</span></td>
                      <td className="text-muted text-xs max-w-[100px] truncate" title={log.dest_info}>{log.dest_info || '—'}</td>
                      <td className="text-muted text-xs whitespace-nowrap">{log.latency_ms != null ? `${log.latency_ms}ms` : '—'}</td>
                      <td className="text-muted text-xs max-w-[180px] truncate" title={log.error}>
                        {log.error ? <span className="text-danger">{log.error}</span> : '—'}
                      </td>
                      <td className="text-muted text-xs whitespace-nowrap">{log.created_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-muted text-center py-8">No logs found</p>
          )}
          {logs.length > 0 && <p className="text-xs text-muted mt-2">Showing {filtered.length} of {logs.length} entries</p>}
        </div>
      </div>
    </div>
  )
}
