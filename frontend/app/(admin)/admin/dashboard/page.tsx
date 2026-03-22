"use client"

import { useQuery } from "@tanstack/react-query"
import { Activity, Bot, FileText, GraduationCap, Users2 } from "lucide-react"
import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { HeroSkeleton, ListCardsSkeleton, StatCardsSkeleton } from "@/components/ui/page-skeletons"
import { getAdminStats } from "@/lib/admin"

const SCHOLARSHIP_COLORS = {
  draft: "#94a3b8",
  open: "#0ea5e9",
  closed: "#f59e0b",
  done: "#10b981",
} as const

const APPLICATION_STATUS_COLORS = {
  draft: "bg-slate-200 text-slate-700",
  submitted: "bg-sky-100 text-sky-800",
  in_review: "bg-amber-100 text-amber-800",
  winner: "bg-emerald-100 text-emerald-800",
  rejected: "bg-rose-100 text-rose-800",
} as const

const ACTIVITY_COLORS = {
  scholarship: "bg-sky-500",
  application: "bg-emerald-500",
  ai_job: "bg-violet-500",
} as const

function formatCompactDate(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat("uz-UZ", {
    month: "short",
    day: "numeric",
  }).format(parsed)
}

function formatDateTime(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }
  return new Intl.DateTimeFormat("uz-UZ", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed)
}

function scholarshipStatusLabel(value: string): string {
  if (value === "draft") {
    return "Draft"
  }
  if (value === "open") {
    return "Open"
  }
  if (value === "closed") {
    return "Closed"
  }
  if (value === "done") {
    return "Done"
  }
  return value
}

function applicationStatusLabel(value: string): string {
  if (value === "draft") {
    return "Draft"
  }
  if (value === "submitted") {
    return "Submitted"
  }
  if (value === "in_review") {
    return "In Review"
  }
  if (value === "winner") {
    return "Winner"
  }
  if (value === "rejected") {
    return "Rejected"
  }
  return value
}

function activityLabel(value: string): string {
  if (value === "scholarship") {
    return "Scholarship"
  }
  if (value === "application") {
    return "Application"
  }
  if (value === "ai_job") {
    return "AI Job"
  }
  return value
}

export default function AdminDashboardPage() {
  const query = useQuery({
    queryKey: ["admin-dashboard-stats"],
    queryFn: getAdminStats,
    retry: 0,
  })

  if (query.isLoading) {
    return (
      <div className="grid gap-6">
        <HeroSkeleton />
        <StatCardsSkeleton />
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <Card className="border-slate-200">
            <CardHeader className="space-y-3">
              <div className="h-6 w-48 animate-pulse rounded-md bg-slate-200/80" />
              <div className="h-4 w-72 animate-pulse rounded-md bg-slate-200/80" />
            </CardHeader>
            <CardContent>
              <div className="h-[320px] animate-pulse rounded-2xl bg-slate-200/80" />
            </CardContent>
          </Card>
          <ListCardsSkeleton count={4} />
        </div>
      </div>
    )
  }

  if (query.isError || !query.data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Dashboardni yuklab bo‘lmadi</CardTitle>
          <CardDescription>`/admin/stats` endpointini tekshiring va qayta urinib ko‘ring.</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const stats = query.data
  const scholarshipPieData = Object.entries(stats.scholarships_by_status).map(([status, value]) => ({
    name: scholarshipStatusLabel(status),
    value,
    color: SCHOLARSHIP_COLORS[status as keyof typeof SCHOLARSHIP_COLORS] ?? "#64748b",
  }))
  const lineData = stats.application_trend.map((item) => ({
    ...item,
    label: formatCompactDate(item.date),
  }))
  const totalSubmittedFlow =
    (stats.applications_by_status.submitted ?? 0) +
    (stats.applications_by_status.in_review ?? 0) +
    (stats.applications_by_status.winner ?? 0) +
    (stats.applications_by_status.rejected ?? 0)

  return (
    <div className="grid gap-6">
      <section className="overflow-hidden rounded-3xl bg-[radial-gradient(circle_at_top_left,_rgba(14,165,233,0.18),_transparent_35%),linear-gradient(135deg,_#0f172a,_#111827_55%,_#1f2937)] p-6 text-white shadow-sm">
        <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-3">
            <Badge className="bg-white/10 text-white hover:bg-white/10">Control Center</Badge>
            <h1 className="max-w-2xl text-3xl font-semibold tracking-tight">
              Universitet stipendiya jarayonlari bitta boshqaruv oynasida.
            </h1>
            <p className="max-w-2xl text-sm text-slate-300">
              Bu panel stipendiyalar oqimi, ariza yuklamasi va AI ishlarining joriy holatini bir ekranda ko‘rsatadi.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="mb-3 flex items-center justify-between">
                <GraduationCap className="h-5 w-5 text-sky-300" />
                <span className="text-xs text-slate-400">Scholarships</span>
              </div>
              <p className="text-3xl font-semibold">{stats.total_scholarships}</p>
              <p className="mt-1 text-xs text-slate-400">Jami ochilgan va yakunlangan dasturlar</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="mb-3 flex items-center justify-between">
                <FileText className="h-5 w-5 text-amber-300" />
                <span className="text-xs text-slate-400">Applications</span>
              </div>
              <p className="text-3xl font-semibold">{stats.total_applications}</p>
              <p className="mt-1 text-xs text-slate-400">Topshirilgan va qayta ko‘rib chiqilgan arizalar</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="mb-3 flex items-center justify-between">
                <Users2 className="h-5 w-5 text-emerald-300" />
                <span className="text-xs text-slate-400">Users</span>
              </div>
              <p className="text-3xl font-semibold">{stats.total_users}</p>
              <p className="mt-1 text-xs text-slate-400">Admin, hakam va talaba profillari</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="mb-3 flex items-center justify-between">
                <Bot className="h-5 w-5 text-violet-300" />
                <span className="text-xs text-slate-400">AI Jobs</span>
              </div>
              <p className="text-3xl font-semibold">{stats.total_ai_jobs}</p>
              <p className="mt-1 text-xs text-slate-400">AI ustun generatsiyasi va review chaqiruvlari</p>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Stipendiyalar Holati</CardTitle>
            <CardDescription>Draft, open, closed va done kesimidagi taqsimot.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6 lg:grid-cols-[280px_1fr]">
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={scholarshipPieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={68}
                    outerRadius={100}
                    paddingAngle={4}
                    strokeWidth={0}
                  >
                    {scholarshipPieData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="grid gap-3 self-center">
              {scholarshipPieData.map((item) => (
                <div key={item.name} className="flex items-center justify-between rounded-xl border border-slate-200 p-3">
                  <div className="flex items-center gap-3">
                    <span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-sm font-medium text-slate-700">{item.name}</span>
                  </div>
                  <span className="text-sm font-semibold text-slate-900">{item.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Ariza Pipeline</CardTitle>
            <CardDescription>Jarayon bo‘yicha hozirgi taqsimot va umumiy oqim.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl bg-slate-950 p-4 text-white">
              <div className="mb-3 flex items-center gap-2">
                <Activity className="h-4 w-4 text-sky-300" />
                <span className="text-sm font-medium">Review throughput</span>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-3xl font-semibold">{totalSubmittedFlow}</p>
                  <p className="mt-1 text-xs text-slate-400">Jarayonga kirgan arizalar</p>
                </div>
                <div>
                  <p className="text-3xl font-semibold">{stats.applications_by_status.winner ?? 0}</p>
                  <p className="mt-1 text-xs text-slate-400">Hozircha g‘olib bo‘lganlar</p>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {Object.entries(stats.applications_by_status).map(([status, value]) => (
                <span
                  key={status}
                  className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${
                    APPLICATION_STATUS_COLORS[status as keyof typeof APPLICATION_STATUS_COLORS] ??
                    "bg-slate-100 text-slate-700"
                  }`}
                >
                  {applicationStatusLabel(status)}
                  <span className="rounded-full bg-white/70 px-1.5 py-0.5 text-[11px]">{value}</span>
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Arizalar Dinamikasi</CardTitle>
            <CardDescription>So‘nggi 7 kun ichida yaratilgan arizalar soni.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[320px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={lineData} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="count"
                    name="Applications"
                    stroke="#0ea5e9"
                    strokeWidth={3}
                    dot={{ r: 4, fill: "#0ea5e9" }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle>Oxirgi Faollik</CardTitle>
            <CardDescription>Yaratilgan stipendiyalar, arizalar va AI ishlarining yangi oqimi.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {stats.recent_activity.length === 0 ? (
              <p className="text-sm text-slate-500">Recent activity hozircha mavjud emas.</p>
            ) : (
              stats.recent_activity.map((item) => (
                <div key={`${item.entity_type}-${item.entity_id}`} className="flex gap-3 rounded-xl border border-slate-200 p-3">
                  <div
                    className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${
                      item.entity_type in ACTIVITY_COLORS
                        ? ACTIVITY_COLORS[item.entity_type as keyof typeof ACTIVITY_COLORS]
                        : "bg-slate-400"
                    }`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-medium text-slate-900">{item.title}</p>
                      <Badge variant="outline">{activityLabel(item.entity_type)}</Badge>
                      {item.status && <Badge variant="secondary">{item.status}</Badge>}
                    </div>
                    {item.subtitle && <p className="mt-1 text-xs text-slate-600">{item.subtitle}</p>}
                    <p className="mt-2 text-[11px] uppercase tracking-wide text-slate-400">
                      {formatDateTime(item.created_at)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
