import Link from "next/link"

import StatusBadge from "@/components/scholarship/StatusBadge"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { ApplicationListItem, Scholarship } from "@/types"

type ScholarshipCardProps = {
  scholarship: Scholarship
  application?: ApplicationListItem
}

function formatDeadline(value: string | null | undefined): string {
  if (!value) {
    return "Ko‘rsatilmagan"
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

function applicationLabel(application?: ApplicationListItem): string | null {
  if (!application) {
    return null
  }
  if (application.status === "draft") {
    return "Qoralama"
  }
  if (application.status === "submitted") {
    return "Topshirilgan"
  }
  if (application.status === "in_review") {
    return "Ko‘rib chiqilmoqda"
  }
  if (application.status === "winner") {
    return "G‘olib"
  }
  return "Rad etilgan"
}

export default function ScholarshipCard({ scholarship, application }: ScholarshipCardProps) {
  const detailHref = `/student/scholarships/${scholarship.id}`
  const primaryHref = application
    ? application.status === "draft"
      ? `/student/scholarships/${scholarship.id}/apply`
      : `/student/applications/${application.id}/result`
    : `/student/scholarships/${scholarship.id}/apply`
  const primaryLabel = application
    ? application.status === "draft"
      ? "Qoralamani davom ettirish"
      : "Natijani ko‘rish"
    : "Ariza topshirish"

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="space-y-2">
            <CardTitle>{scholarship.title}</CardTitle>
            <CardDescription>{scholarship.description || "Tavsif ko‘rsatilmagan."}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge status={scholarship.status} />
            <Badge variant="secondary">Deadline: {formatDeadline(scholarship.deadline)}</Badge>
            <Badge variant="outline">Winners: {scholarship.max_winners}</Badge>
            {applicationLabel(application) && <Badge variant="outline">{applicationLabel(application)}</Badge>}
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1 text-sm text-slate-600">
          <p>Ariza formasi scholarship detail sahifasida mezonlar asosida dinamik chiqadi.</p>
          {scholarship.ai_analysis_enabled && <p className="text-sky-700">AI tahlil bu stipendiya uchun yoqilgan.</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={detailHref} className={cn(buttonVariants({ variant: "outline" }))}>
            Batafsil
          </Link>
          <Link href={primaryHref} className={cn(buttonVariants({ variant: "outline" }))}>
            {primaryLabel}
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}
