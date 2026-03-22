import { HeroSkeleton, StatCardsSkeleton, TableCardSkeleton } from "@/components/ui/page-skeletons"

export default function AdminLoading() {
  return (
    <div className="grid gap-6">
      <HeroSkeleton />
      <StatCardsSkeleton />
      <TableCardSkeleton rows={6} columns={6} />
    </div>
  )
}
