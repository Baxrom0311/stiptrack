import { DetailPageSkeleton, TableCardSkeleton } from "@/components/ui/page-skeletons"

export default function JuryLoading() {
  return (
    <div className="grid gap-6">
      <TableCardSkeleton rows={6} columns={6} />
      <DetailPageSkeleton />
    </div>
  )
}
