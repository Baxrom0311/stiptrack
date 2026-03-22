import Link from "next/link"
import { AlertTriangle } from "lucide-react"

type ErrorStateProps = {
  title: string
  description: string
  retryLabel?: string
  onRetry?: () => void
  backHref?: string
  backLabel?: string
}

export default function ErrorState({
  title,
  description,
  retryLabel = "Qayta urinish",
  onRetry,
  backHref = "/",
  backLabel = "Bosh sahifa",
}: ErrorStateProps) {
  return (
    <div className="mx-auto flex min-h-[60vh] w-full max-w-2xl items-center justify-center px-4 py-10">
      <div className="w-full rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 text-rose-700">
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h1 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-slate-600">{description}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex h-8 items-center justify-center rounded-lg bg-slate-900 px-3 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              {retryLabel}
            </button>
          ) : null}
          <Link
            href={backHref}
            className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
          >
            {backLabel}
          </Link>
        </div>
      </div>
    </div>
  )
}
