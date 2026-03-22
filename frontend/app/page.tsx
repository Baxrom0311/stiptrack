import Link from "next/link"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center px-4 py-8">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Stipendiya Platform</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700">
          <p>Project scaffold is ready. Continue with auth and feature modules in next tasks.</p>
          <div className="flex flex-wrap gap-3">
            <Link className="underline" href="/login">
              Login
            </Link>
            <Link className="underline" href="/register">
              Register
            </Link>
            <Link className="underline" href="/admin/dashboard">
              Admin Dashboard
            </Link>
            <Link className="underline" href="/jury/dashboard">
              Jury Dashboard
            </Link>
            <Link className="underline" href="/student/dashboard">
              Student Dashboard
            </Link>
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
