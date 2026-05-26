import { ReactNode, useEffect } from 'react'

export default function DialogModal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-surface border border-border rounded-xl shadow-2xl p-6 w-full max-w-xl mx-4 max-h-[90vh] overflow-y-auto">
        {children}
      </div>
    </div>
  )
}
