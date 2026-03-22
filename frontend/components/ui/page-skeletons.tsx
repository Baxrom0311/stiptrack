import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

type ClassNameProps = {
  className?: string
}

export function HeroSkeleton({ className }: ClassNameProps) {
  return (
    <section className={cn("rounded-3xl border border-slate-200 bg-white p-6 shadow-sm", className)}>
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <Skeleton className="h-6 w-28 rounded-full" />
          <Skeleton className="h-10 w-full max-w-2xl" />
          <Skeleton className="h-4 w-full max-w-3xl" />
          <Skeleton className="h-4 w-full max-w-2xl" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-10 w-32 rounded-xl" />
          <Skeleton className="h-10 w-36 rounded-xl" />
        </div>
      </div>
    </section>
  )
}

export function StatCardsSkeleton({ className, count = 4 }: ClassNameProps & { count?: number }) {
  return (
    <div className={cn("grid gap-4 md:grid-cols-2 xl:grid-cols-4", className)}>
      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} className="border-slate-200">
          <CardHeader className="space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-36" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-10 w-20" />
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function TableCardSkeleton({
  className,
  rows = 5,
  columns = 5,
  withToolbar = true,
}: ClassNameProps & {
  rows?: number
  columns?: number
  withToolbar?: boolean
}) {
  return (
    <Card className={cn("border-slate-200", className)}>
      <CardHeader className="space-y-3">
        <Skeleton className="h-6 w-44" />
        <Skeleton className="h-4 w-72" />
        {withToolbar && (
          <div className="grid gap-3 md:grid-cols-3">
            <Skeleton className="h-10 w-full rounded-xl" />
            <Skeleton className="h-10 w-full rounded-xl" />
            <Skeleton className="h-10 w-full rounded-xl" />
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-12">
          {Array.from({ length: columns }).map((_, index) => (
            <Skeleton key={index} className="h-4 w-full md:col-span-2" />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="grid grid-cols-1 gap-3 rounded-2xl border border-slate-100 p-4 md:grid-cols-12">
            {Array.from({ length: columns }).map((_, columnIndex) => (
              <Skeleton
                key={columnIndex}
                className={cn("h-4 w-full", columnIndex === 0 ? "md:col-span-4" : "md:col-span-2")}
              />
            ))}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

export function FormCardSkeleton({
  className,
  fields = 4,
  actions = 1,
}: ClassNameProps & { fields?: number; actions?: number }) {
  return (
    <Card className={cn("border-slate-200", className)}>
      <CardHeader className="space-y-3">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-72" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: fields }).map((_, index) => (
            <div key={index} className="space-y-2">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-10 w-full rounded-xl" />
            </div>
          ))}
        </div>
        <div className="flex justify-end gap-3">
          {Array.from({ length: actions }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-32 rounded-xl" />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export function ListCardsSkeleton({ className, count = 3 }: ClassNameProps & { count?: number }) {
  return (
    <div className={cn("grid gap-4", className)}>
      {Array.from({ length: count }).map((_, index) => (
        <Card key={index} className="border-slate-200">
          <CardHeader className="space-y-3">
            <Skeleton className="h-6 w-52" />
            <Skeleton className="h-4 w-72" />
          </CardHeader>
          <CardContent className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-10/12" />
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-8 w-20 rounded-full" />
              <Skeleton className="h-8 w-24 rounded-full" />
              <Skeleton className="h-8 w-28 rounded-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

export function DetailPageSkeleton({ className }: ClassNameProps) {
  return (
    <div className={cn("grid gap-6 xl:grid-cols-[1.2fr_1fr]", className)}>
      <div className="space-y-6">
        <FormCardSkeleton fields={2} />
        <ListCardsSkeleton count={2} />
      </div>
      <Card className="border-slate-200">
        <CardHeader className="space-y-3">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-56" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <Skeleton className="h-10 w-full rounded-xl" />
            <Skeleton className="h-10 w-full rounded-xl" />
          </div>
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="space-y-2 rounded-2xl border border-slate-100 p-4">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-10 w-full rounded-xl" />
            </div>
          ))}
          <div className="flex justify-end gap-3">
            <Skeleton className="h-10 w-28 rounded-xl" />
            <Skeleton className="h-10 w-36 rounded-xl" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
