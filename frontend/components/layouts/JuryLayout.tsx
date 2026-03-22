import Link from "next/link"
import { ReactNode } from "react"

export default function JuryLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-amber-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-3 py-3 sm:px-4 lg:flex-row lg:items-center lg:justify-between">
          <h1 className="text-lg font-semibold">Jury Panel</h1>
          <nav className="-mx-1 flex flex-wrap items-center gap-2 text-sm text-slate-600">
            <Link className="rounded-lg px-2 py-1 hover:bg-amber-100" href="/jury/dashboard">
              Dashboard
            </Link>
            <Link className="rounded-lg px-2 py-1 hover:bg-amber-100" href="/jury/applications">
              Applications
            </Link>
            <Link className="rounded-lg px-2 py-1 hover:bg-amber-100" href="/jury/profile">
              Profile
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-3 py-5 sm:px-4 sm:py-6">{children}</main>
    </div>
  )
}
