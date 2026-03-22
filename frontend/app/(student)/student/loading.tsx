import { FormCardSkeleton, StatCardsSkeleton, TableCardSkeleton } from "@/components/ui/page-skeletons"

export default function StudentLoading() {
  return (
    <div className="grid gap-6">
      <StatCardsSkeleton />
      <TableCardSkeleton rows={5} columns={5} withToolbar={false} />
      <FormCardSkeleton fields={4} />
    </div>
  )
}
