"use client"

import { useMemo, useState } from "react"

import ScholarshipCard from "@/components/scholarship/ScholarshipCard"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { ListCardsSkeleton } from "@/components/ui/page-skeletons"
import { useMyApplications } from "@/hooks/useApplications"
import { useScholarships } from "@/hooks/useScholarships"
import type { ApplicationListItem, Scholarship } from "@/types"

type StudentScholarshipFilter = "all" | "mine" | "new" | "ai"

function findApplication(scholarship: Scholarship, applications: ApplicationListItem[]): ApplicationListItem | undefined {
  return applications.find((item) => item.scholarship_id === scholarship.id)
}

export default function StudentScholarshipsPage() {
  const [search, setSearch] = useState("")
  const [filter, setFilter] = useState<StudentScholarshipFilter>("all")
  const scholarshipsQuery = useScholarships({ status: "open", limit: 100 })
  const applicationsQuery = useMyApplications()

  const filteredScholarships = useMemo(() => {
    const scholarships = scholarshipsQuery.data ?? []
    const applications = applicationsQuery.data ?? []
    const normalizedSearch = search.trim().toLowerCase()

    return scholarships.filter((scholarship) => {
      if (normalizedSearch) {
        const haystack = `${scholarship.title} ${scholarship.description ?? ""}`.toLowerCase()
        if (!haystack.includes(normalizedSearch)) {
          return false
        }
      }

      const application = findApplication(scholarship, applications)

      if (filter === "mine") {
        return Boolean(application)
      }

      if (filter === "new") {
        return !application
      }

      if (filter === "ai") {
        return scholarship.ai_analysis_enabled
      }

      return true
    })
  }, [applicationsQuery.data, filter, scholarshipsQuery.data, search])

  if (scholarshipsQuery.isLoading || applicationsQuery.isLoading) {
    return <ListCardsSkeleton count={4} />
  }

  return (
    <div className="grid gap-6">
      <section className="rounded-3xl bg-[linear-gradient(135deg,_#eff6ff,_#f0fdf4_55%,_#f8fafc)] p-6 ring-1 ring-sky-200">
        <Badge variant="outline">Open Scholarships</Badge>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">Ochiq stipendiyalar</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          Qidiruv va filter orqali mos grantni toping, detailni ko‘ring va ariza topshiring.
        </p>
      </section>

      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle>Qidiruv va filter</CardTitle>
          <CardDescription>Faqat ochiq stipendiyalar ko‘rsatiladi.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nomi yoki tavsifi bo‘yicha qidiring..." />
          <select
            className="flex h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            value={filter}
            onChange={(event) => setFilter(event.target.value as StudentScholarshipFilter)}
          >
            <option value="all">Barchasi</option>
            <option value="mine">Arizam bor</option>
            <option value="new">Hali topshirmaganman</option>
            <option value="ai">AI yoqilgan</option>
          </select>
        </CardContent>
      </Card>

      {(scholarshipsQuery.isError || applicationsQuery.isError) && (
        <Card>
          <CardHeader>
            <CardTitle>Ma’lumotlarni yuklab bo‘lmadi</CardTitle>
            <CardDescription>Scholarship yoki ariza holatini olishda xatolik yuz berdi.</CardDescription>
          </CardHeader>
        </Card>
      )}

      {!scholarshipsQuery.isError && filteredScholarships.length === 0 && (
        <Card>
          <CardContent className="pt-6">
            <EmptyState
              title={(scholarshipsQuery.data?.length ?? 0) === 0 ? "Ochiq stipendiyalar yo‘q" : "Mos stipendiya topilmadi"}
              description={
                (scholarshipsQuery.data?.length ?? 0) === 0
                  ? "Yangi stipendiyalar ochilganda shu sahifada paydo bo‘ladi."
                  : "Qidiruv yoki filter shartlariga mos ochiq stipendiya topilmadi."
              }
            />
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4">
        {filteredScholarships.map((scholarship) => (
          <ScholarshipCard
            key={scholarship.id}
            scholarship={scholarship}
            application={findApplication(scholarship, applicationsQuery.data ?? [])}
          />
        ))}
      </div>
    </div>
  )
}
