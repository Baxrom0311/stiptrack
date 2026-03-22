"use client"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import type { ApplicationStatus, ApplicationStatusLogEntry } from "@/types"

type ApplicationStatusHistoryProps = {
  logs: ApplicationStatusLogEntry[]
  title?: string
  description?: string
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-"
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat("uz-UZ", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed)
}

function statusLabel(status: ApplicationStatus | null | undefined): string {
  if (!status) {
    return "Yangi"
  }
  if (status === "draft") {
    return "Qoralama"
  }
  if (status === "submitted") {
    return "Topshirilgan"
  }
  if (status === "in_review") {
    return "Ko‘rib chiqilmoqda"
  }
  if (status === "winner") {
    return "G‘olib"
  }
  return "Rad etilgan"
}

function sourceLabel(source: string): string {
  if (source === "student_apply") {
    return "Talaba yaratdi"
  }
  if (source === "student_submit") {
    return "Talaba topshirdi"
  }
  if (source === "jury_review_started") {
    return "Hakam review"
  }
  if (source === "admin_manual") {
    return "Admin"
  }
  if (source === "winner_announcement") {
    return "Winner hisob"
  }
  if (source === "appeal_decision") {
    return "Apellyatsiya"
  }
  return "Tizim"
}

export default function ApplicationStatusHistory({
  logs,
  title = "Ariza tarixi",
  description = "Holat o‘zgarishlari ketma-ketligi shu yerda ko‘rinadi.",
}: ApplicationStatusHistoryProps) {
  return (
    <Card className="border-slate-200">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {logs.length === 0 ? (
          <EmptyState
            title="Status log hali yo‘q"
            description="Bu ariza uchun tarix yozuvlari hali shakllanmagan."
          />
        ) : (
          <div className="space-y-3">
            {logs.map((log) => (
              <div key={log.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">{sourceLabel(log.source)}</Badge>
                  <Badge variant="secondary">{formatDate(log.created_at)}</Badge>
                  <Badge variant="outline">
                    {statusLabel(log.previous_status)} {"->"} {statusLabel(log.new_status)}
                  </Badge>
                  {log.changed_by_user?.full_name && (
                    <Badge variant="outline">By: {log.changed_by_user.full_name}</Badge>
                  )}
                </div>
                {log.note && <p className="mt-3 text-sm text-slate-700">{log.note}</p>}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
