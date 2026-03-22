import { ReactNode } from "react"

import StudentLayout from "@/components/layouts/StudentLayout"

export default function StudentGroupLayout({ children }: { children: ReactNode }) {
  return <StudentLayout>{children}</StudentLayout>
}
