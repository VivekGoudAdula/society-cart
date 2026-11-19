import React from 'react'
import { ShoppingCart, CheckCircle2 } from 'lucide-react'

/**
 * Society Cart Development Placeholder Component.
 * Serves as the minimal verified entry point for Phase 0.
 */
export default function App(): React.JSX.Element {
  return (
    <div className="flex min-h-screen items-center justify-center p-6 bg-slate-50 text-slate-800">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-sm border border-slate-200 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 mb-4">
          <ShoppingCart className="h-7 w-7" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Society Cart</h1>
        <p className="mt-1 text-sm font-medium text-emerald-600">Your Society. One Chat. One Bulk Order.</p>
        <p className="mt-3 text-xs text-slate-500">Nexconn Build Challenge 2026 — Track: Social & Community</p>
        
        <div className="mt-6 flex items-center justify-center gap-2 rounded-lg bg-emerald-50/70 px-4 py-2 text-xs font-semibold text-emerald-700 border border-emerald-100">
          <CheckCircle2 className="h-4 w-4" />
          <span>Phase 0: Workspace & Architecture Ready</span>
        </div>
      </div>
    </div>
  )
}
