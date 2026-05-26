import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function Dashboard() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.stats().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-muted">Loading...</p>

  const stats = [
    { label: 'Accounts', value: data?.accounts ?? 0 },
    { label: 'Active Rules', value: data?.active_rules ?? 0 },
    { label: 'Forwards (24h)', value: data?.forwards_24h ?? 0 },
    { label: 'Errors (24h)', value: data?.errors_24h ?? 0 },
  ]

  return (
    <div>
      <div className="page-header mb-6">
        <h2 className="text-xl font-semibold">Dashboard</h2>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {stats.map((s) => (
          <div key={s.label} className="card card-body text-center">
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="card">
        <div className="card-header"><h3 className="font-semibold">Recent Activity</h3></div>
        <div className="card-body">
          {data?.recent_activity?.length ? (
            <table className="table">
              <thead>
                <tr><th>Rule</th><th>Status</th><th>Dest</th><th>Latency</th><th>Time</th></tr>
              </thead>
              <tbody>
                {data.recent_activity.map((log: any) => (
                  <tr key={log.id}>
                    <td className="text-muted">{log.rule_name}</td>
                    <td><span className={`badge badge-${log.status}`}>{log.status}</span></td>
                    <td className="text-muted">{log.dest_info || '—'}</td>
                    <td className="text-muted">{log.latency_ms}ms</td>
                    <td className="text-muted text-xs">{log.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-muted text-center py-8">No recent activity</p>
          )}
        </div>
      </div>
    </div>
  )
}
