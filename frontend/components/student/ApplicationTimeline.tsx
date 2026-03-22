"use client"

import type { ApplicationStatus } from "@/types"
import { cn } from "@/lib/utils"

type ApplicationTimelineProps = {
  status: ApplicationStatus
  compact?: boolean
}

type StepState = "done" | "current" | "pending"

const BASE_STEPS: string[] = ["Qoralama", "Topshirildi", "Ko‘rib chiqish", "Yakun"]

function resolveCurrentIndex(status: ApplicationStatus): number {
  if (status === "draft") {
    return 0
  }
  if (status === "submitted") {
    return 1
  }
  if (status === "in_review") {
    return 2
  }
  return 3
}

function resolveFinalLabel(status: ApplicationStatus): string {
  if (status === "winner") {
    return "G‘olib"
  }
  if (status === "rejected") {
    return "Rad etildi"
  }
  return "Yakun"
}

function resolveStepState(index: number, currentIndex: number): StepState {
  if (index < currentIndex) {
    return "done"
  }
  if (index === currentIndex) {
    return "current"
  }
  return "pending"
}

function dotClassName(state: StepState) {
  if (state === "done") {
    return "bg-emerald-500 ring-emerald-200"
  }
  if (state === "current") {
    return "bg-sky-500 ring-sky-200"
  }
  return "bg-slate-300 ring-slate-200"
}

function textClassName(state: StepState) {
  if (state === "done") {
    return "text-emerald-700"
  }
  if (state === "current") {
    return "text-sky-700"
  }
  return "text-slate-500"
}

export default function ApplicationTimeline({ status, compact = false }: ApplicationTimelineProps) {
  const currentIndex = resolveCurrentIndex(status)
  const steps = [...BASE_STEPS]
  steps[3] = resolveFinalLabel(status)

  return (
    <div className={cn("flex items-start gap-1.5", compact && "gap-1")}>
      {steps.map((step, index) => {
        const state = resolveStepState(index, currentIndex)
        return (
          <div key={`${step}-${index}`} className="flex min-w-0 items-center">
            <div className="flex min-w-0 flex-col items-center">
              <span
                className={cn(
                  "h-2.5 w-2.5 rounded-full ring-3 transition-colors",
                  compact && "h-2 w-2 ring-2",
                  dotClassName(state),
                )}
              />
              <span
                className={cn(
                  "mt-1 text-center text-[11px] font-medium leading-tight",
                  compact && "text-[10px]",
                  textClassName(state),
                )}
              >
                {step}
              </span>
            </div>
            {index < steps.length - 1 && (
              <span
                className={cn(
                  "mx-1 mt-[-12px] block h-[2px] w-4 rounded bg-slate-200",
                  compact && "mx-0.5 mt-[-10px] w-3",
                  index < currentIndex && "bg-emerald-300",
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
