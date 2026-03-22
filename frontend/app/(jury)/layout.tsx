import { ReactNode } from "react"

import JuryLayout from "@/components/layouts/JuryLayout"

export default function JuryGroupLayout({ children }: { children: ReactNode }) {
  return <JuryLayout>{children}</JuryLayout>
}
