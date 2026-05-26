const BASE = '/api/v1'

async function req<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json', ...opts?.headers },
    ...opts,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw { status: res.status, ...body }
  }
  return res.json()
}

export const api = {
  stats: () => req<any>('/stats'),
  accounts: {
    list: () => req<any>('/accounts'),
    delete: (id: number) => req(`/accounts/${id}`, { method: 'DELETE' }),
    addBot: (data: { name: string; bot_token: string }) =>
      req<any>('/accounts/bot', { method: 'POST', body: JSON.stringify(data) }),
    sendCode: (data: { name: string; phone: string }) =>
      req<any>('/accounts/user/send-code', { method: 'POST', body: JSON.stringify(data) }),
    verifyCode: (data: { code: string; password?: string }) =>
      req<any>('/accounts/user/verify', { method: 'POST', body: JSON.stringify(data) }),
  },
  rules: {
    list: () => req<any>('/rules'),
    create: (data: any) => req<any>('/rules', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: any) =>
      req<any>(`/rules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    toggle: (id: number) => req<any>(`/rules/${id}/toggle`, { method: 'POST' }),
    delete: (id: number) => req(`/rules/${id}`, { method: 'DELETE' }),
    dialogs: (accountId: number) => req<any>(`/rules/dialogs?account_id=${accountId}`),
  },
  logs: {
    list: (params?: { rule_id?: number; limit?: number }) => {
      const q = new URLSearchParams()
      if (params?.rule_id) q.set('rule_id', String(params.rule_id))
      if (params?.limit) q.set('limit', String(params.limit))
      return req<any>(`/logs?${q}`)
    },
    clear: () => req('/logs', { method: 'DELETE' }),
  },
  settings: {
    get: () => req<any>('/settings'),
    saveApi: (api_id: string, api_hash: string) =>
      req<any>('/settings/api', {
        method: 'PUT',
        body: JSON.stringify({ api_id, api_hash }),
      }),
    addWebhook: (data: { name: string; url: string; secret?: string }) =>
      req<any>('/settings/webhooks', { method: 'POST', body: JSON.stringify(data) }),
    deleteWebhook: (id: number) =>
      req(`/settings/webhooks/${id}`, { method: 'DELETE' }),
    testWebhook: (id: number) =>
      req<any>(`/settings/webhooks/${id}/test`, { method: 'POST' }),
  },
}
