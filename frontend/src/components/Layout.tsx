import { ReactNode } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/router'

const navItems = [
  { href: '/', label: 'Dashboard', icon: '▤' },
  { href: '/accounts', label: 'Accounts', icon: '●' },
  { href: '/rules', label: 'Rules', icon: '▶' },
  { href: '/logs', label: 'Logs', icon: '☰' },
  { href: '/settings', label: 'Settings', icon: '⚙' },
]

export default function Layout({ children }: { children: ReactNode }) {
  const router = useRouter()

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-surface border-r border-border flex-shrink-0 p-6 flex flex-col">
        <div className="mb-8">
          <h1 className="text-xl font-bold text-primary">TeleBridge</h1>
          <p className="text-xs text-muted mt-0.5">Message Relay Hub</p>
        </div>
        <nav className="flex flex-col gap-0.5">
          {navItems.map((item) => {
            const active = router.pathname === item.href || router.pathname.startsWith(item.href + '/')
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  active
                    ? 'bg-primary text-white'
                    : 'text-muted hover:bg-surface2 hover:text-[#e4e6f0]'
                }`}
              >
                <span className="w-4 text-center text-xs">{item.icon}</span>
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>
      <main className="flex-1 p-8 max-w-6xl overflow-x-auto">{children}</main>
    </div>
  )
}
