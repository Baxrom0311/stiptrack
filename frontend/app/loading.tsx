import { HeroSkeleton, StatCardsSkeleton, TableCardSkeleton } from "@/components/ui/page-skeletons"

export default function RootLoading() {
  return (
    <div className="mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6">
      <HeroSkeleton />
      <StatCardsSkeleton />
      <TableCardSkeleton />
    </div>
  )
}
