"use client"

import Link from "next/link"

import ApplicationTimeline from "@/components/student/ApplicationTimeline"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { TableCardSkeleton } from "@/components/ui/page-skeletons"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useMyApplications } from "@/hooks/useApplications"
import { cn } from "@/lib/utils"
import type { ApplicationStatus } from "@/types"

function statusLabel(status: ApplicationStatus): string {
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
  if (status === "rejected") {
    return "Rad etilgan"
  }
  return status
}

function statusVariant(status: ApplicationStatus): "default" | "secondary" | "outline" | "destructive" {
  if (status === "winner") {
    return "default"
  }
  if (status === "rejected") {
    return "destructive"
  }
  if (status === "submitted") {
    return "secondary"
  }
  return "outline"
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

export default function StudentApplicationsPage() {
  const query = useMyApplications()

  if (query.isLoading) {
    return <TableCardSkeleton rows={6} columns={6} withToolbar={false} />
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Mening Arizalarim</CardTitle>
          <CardDescription>Stipendiya arizalaringiz holati va natijalariga o‘ting.</CardDescription>
        </CardHeader>
        <CardContent>
          {query.isError && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              Arizalarni yuklab bo‘lmadi. Tizimga qayta kirib urinib ko‘ring.
            </div>
          )}

          {!query.isLoading && !query.isError && (query.data?.length ?? 0) === 0 && (
            <EmptyState
              title="Arizalar hali yo‘q"
              description="Topshirilgan stipendiya arizalaringiz shu yerda ko‘rinadi. Yangi grant ochilganda birinchi arizani yuborasiz."
            />
          )}

          {!query.isLoading && !query.isError && (query.data?.length ?? 0) > 0 && (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Stipendiya</TableHead>
                  <TableHead>Holat</TableHead>
                  <TableHead>Jarayon</TableHead>
                  <TableHead>Umumiy ball</TableHead>
                  <TableHead>Topshirilgan sana</TableHead>
                  <TableHead className="text-right">Tahlil</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(query.data ?? []).map((application) => (
                  <TableRow key={application.id}>
                    <TableCell className="font-medium">{application.scholarship?.title ?? "-"}</TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(application.status)}>{statusLabel(application.status)}</Badge>
                    </TableCell>
                    <TableCell className="max-w-[240px]">
                      <ApplicationTimeline status={application.status} compact />
                    </TableCell>
                    <TableCell>
                      {typeof application.total_score === "number" ? application.total_score.toFixed(2) : "-"}
                    </TableCell>
                    <TableCell>{formatDate(application.submitted_at)}</TableCell>
                    <TableCell className="text-right">
                      <Link
                        href={`/student/applications/${application.id}/result`}
                        className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                      >
                        Natija/Tahlil
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
