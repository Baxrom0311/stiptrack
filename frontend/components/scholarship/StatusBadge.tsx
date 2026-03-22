import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { ScholarshipStatus } from "@/types"

type StatusBadgeProps = {
  status: ScholarshipStatus
  className?: string
}

function labelForStatus(status: ScholarshipStatus): string {
  if (status === "draft") {
    return "Draft"
  }
  if (status === "open") {
    return "Open"
  }
  if (status === "closed") {
    return "Closed"
  }
  return "Done"
}

function classesForStatus(status: ScholarshipStatus): string {
  if (status === "draft") {
    return "border-slate-200 bg-slate-100 text-slate-700"
  }
  if (status === "open") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700"
  }
  if (status === "closed") {
    return "border-amber-200 bg-amber-50 text-amber-700"
  }
  return "border-sky-200 bg-sky-50 text-sky-700"
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge variant="outline" className={cn(classesForStatus(status), className)}>
      {labelForStatus(status)}
    </Badge>
  )
}
