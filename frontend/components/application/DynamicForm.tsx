"use client"

import { Loader2, Save } from "lucide-react"
import { useEffect, useMemo, useRef, useState } from "react"

import FileUpload from "@/components/application/FileUpload"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import type { Column } from "@/types"

export type DynamicFormValues = Record<string, string | null>

type DynamicFormProps = {
  columns: Column[]
  initialValues?: DynamicFormValues
  disabled?: boolean
  submitAttempted?: boolean
  onValuesChange?: (values: DynamicFormValues) => void
  onAutosave?: (values: DynamicFormValues) => Promise<void>
  onFileUpload?: (column: Column, file: File, onProgress: (progress: number) => void) => Promise<string>
  onFileDelete?: (column: Column) => Promise<void>
}

type AutosaveState = "idle" | "saving" | "saved" | "error"

function normalizeTextValue(value: string | null | undefined): string | null {
  if (value == null) {
    return null
  }
  return value
}

export function buildDynamicInitialValues(columns: Column[], values: Array<{ column_id: string; value_text?: string | null; value_file_url?: string | null }>) {
  const result: DynamicFormValues = {}

  for (const column of columns) {
    const value = values.find((item) => item.column_id === column.id)
    result[column.id] = value?.value_file_url ?? value?.value_text ?? null
  }

  return result
}

export function buildAutosavePayload(columns: Column[], values: DynamicFormValues): DynamicFormValues {
  const payload: DynamicFormValues = {}

  for (const column of columns) {
    const value = values[column.id] ?? null
    if (column.field_type === "file") {
      if (value === null) {
        payload[column.id] = null
      }
      continue
    }
    payload[column.id] = normalizeTextValue(value)
  }

  return payload
}

function hasValue(column: Column, value: string | null | undefined): boolean {
  if (column.field_type === "file") {
    return Boolean(value)
  }
  return typeof value === "string" ? value.trim().length > 0 : false
}

export function validateDynamicValues(columns: Column[], values: DynamicFormValues): Record<string, string> {
  const errors: Record<string, string> = {}

  for (const column of columns) {
    const value = values[column.id] ?? null

    if (column.is_required && !hasValue(column, value)) {
      errors[column.id] = "Bu maydon majburiy."
      continue
    }

    if (!value) {
      continue
    }

    if (column.field_type === "url") {
      try {
        const parsed = new URL(value)
        if (!(parsed.protocol === "http:" || parsed.protocol === "https:")) {
          errors[column.id] = "URL `http` yoki `https` bilan boshlanishi kerak."
        }
      } catch {
        errors[column.id] = "To‘g‘ri URL kiriting."
      }
    }

    if (column.field_type === "number") {
      const numericValue = Number(value)
      if (Number.isNaN(numericValue)) {
        errors[column.id] = "Raqam kiriting."
        continue
      }
      if (column.input_min != null && numericValue < column.input_min) {
        errors[column.id] = `Qiymat ${column.input_min} dan kichik bo‘lishi mumkin emas.`
        continue
      }
      if (column.input_max != null && numericValue > column.input_max) {
        errors[column.id] = `Qiymat ${column.input_max} dan katta bo‘lishi mumkin emas.`
      }
    }

    if (column.field_type === "select" && column.select_options?.length && !column.select_options.includes(value)) {
      errors[column.id] = "Qiymat tanlangan variantlardan biri bo‘lishi kerak."
    }
  }

  return errors
}

function AutosaveBadge({ state }: { state: AutosaveState }) {
  if (state === "saving") {
    return (
      <Badge variant="secondary" className="gap-1">
        <Loader2 className="h-3 w-3 animate-spin" />
        Draft saqlanmoqda
      </Badge>
    )
  }

  if (state === "saved") {
    return (
      <Badge variant="outline" className="gap-1 border-emerald-200 bg-emerald-50 text-emerald-700">
        <Save className="h-3 w-3" />
        Draft saqlandi
      </Badge>
    )
  }

  if (state === "error") {
    return <Badge variant="destructive">Draft saqlanmadi</Badge>
  }

  return <Badge variant="outline">Avto-save 2s</Badge>
}

export default function DynamicForm({
  columns,
  initialValues = {},
  disabled,
  submitAttempted,
  onValuesChange,
  onAutosave,
  onFileUpload,
  onFileDelete,
}: DynamicFormProps) {
  const initialSerialized = useMemo(() => JSON.stringify(initialValues), [initialValues])
  const [values, setValues] = useState<DynamicFormValues>(initialValues)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [autosaveState, setAutosaveState] = useState<AutosaveState>("idle")
  const lastSavedRef = useRef(initialSerialized)

  useEffect(() => {
    setValues(initialValues)
    setErrors({})
    setAutosaveState("idle")
    lastSavedRef.current = initialSerialized
  }, [initialSerialized, initialValues])

  useEffect(() => {
    onValuesChange?.(values)
  }, [onValuesChange, values])

  useEffect(() => {
    if (!submitAttempted) {
      return
    }
    setErrors(validateDynamicValues(columns, values))
  }, [columns, submitAttempted, values])

  useEffect(() => {
    if (!onAutosave) {
      return
    }

    const payload = buildAutosavePayload(columns, values)
    const serialized = JSON.stringify(payload)
    if (serialized === lastSavedRef.current) {
      return
    }

    setAutosaveState("saving")
    const timer = window.setTimeout(async () => {
      try {
        await onAutosave(payload)
        lastSavedRef.current = JSON.stringify(payload)
        setAutosaveState("saved")
      } catch {
        setAutosaveState("error")
      }
    }, 2000)

    return () => window.clearTimeout(timer)
  }, [columns, onAutosave, values])

  function setFieldValue(column: Column, nextValue: string | null) {
    setValues((current) => ({
      ...current,
      [column.id]: nextValue,
    }))

    const nextErrors = validateDynamicValues(columns, {
      ...values,
      [column.id]: nextValue,
    })
    setErrors(nextErrors)
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
        <div>
          <p className="text-sm font-medium text-slate-900">Dinamik ariza formasi</p>
          <p className="text-xs text-slate-500">Har bir maydon scholarship ustunlariga qarab avtomatik chiqadi.</p>
        </div>
        <AutosaveBadge state={autosaveState} />
      </div>

      <div className="grid gap-5">
        {columns.map((column) => {
          const value = values[column.id] ?? null
          const error = errors[column.id]
          const label = (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-slate-900">{column.name}</span>
              {column.is_required && <span className="text-rose-600">*</span>}
              {column.ai_analyze && <Badge variant="outline">AI analyze</Badge>}
            </div>
          )

          return (
            <div key={column.id} className="space-y-2 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="space-y-1">
                {label}
                {column.description && <p className="text-sm text-slate-500">{column.description}</p>}
              </div>

              {column.field_type === "text" && (
                <Input
                  value={value ?? ""}
                  disabled={disabled}
                  aria-invalid={Boolean(error)}
                  placeholder="Javobingizni kiriting"
                  onChange={(event) => setFieldValue(column, event.target.value)}
                />
              )}

              {column.field_type === "textarea" && (
                <div className="space-y-2">
                  <Textarea
                    value={value ?? ""}
                    disabled={disabled}
                    aria-invalid={Boolean(error)}
                    placeholder="Batafsil yozing"
                    onChange={(event) => setFieldValue(column, event.target.value)}
                  />
                  <div className="text-right text-xs text-slate-500">{(value ?? "").length} belgi</div>
                </div>
              )}

              {column.field_type === "number" && (
                <div className="space-y-2">
                  <Input
                    type="number"
                    step="any"
                    value={value ?? ""}
                    disabled={disabled}
                    aria-invalid={Boolean(error)}
                    min={column.input_min ?? undefined}
                    max={column.input_max ?? undefined}
                    placeholder="Raqam kiriting"
                    onChange={(event) => setFieldValue(column, event.target.value)}
                  />
                  {(column.input_min != null || column.input_max != null) && (
                    <p className="text-xs text-slate-500">
                      Ruxsat etilgan oraliq: {column.input_min ?? "-"} - {column.input_max ?? "-"}
                    </p>
                  )}
                </div>
              )}

              {column.field_type === "date" && (
                <Input
                  type="date"
                  value={value ?? ""}
                  disabled={disabled}
                  aria-invalid={Boolean(error)}
                  onChange={(event) => setFieldValue(column, event.target.value)}
                />
              )}

              {column.field_type === "select" && (
                <select
                  className={cn(
                    "flex h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
                    error && "border-rose-300",
                  )}
                  value={value ?? ""}
                  disabled={disabled}
                  onChange={(event) => setFieldValue(column, event.target.value || null)}
                >
                  <option value="">Tanlang</option>
                  {(column.select_options ?? []).map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              )}

              {column.field_type === "url" && (
                <Input
                  type="url"
                  value={value ?? ""}
                  disabled={disabled}
                  aria-invalid={Boolean(error)}
                  placeholder="https://example.com"
                  onChange={(event) => setFieldValue(column, event.target.value)}
                />
              )}

              {column.field_type === "file" && onFileUpload && (
                <FileUpload
                  kind="application"
                  value={value}
                  disabled={disabled}
                  onUpload={async (file, onProgress) => {
                    const uploadedUrl = await onFileUpload(column, file, onProgress)
                    setFieldValue(column, uploadedUrl)
                  }}
                  onDelete={
                    onFileDelete
                      ? async () => {
                          await onFileDelete(column)
                          setFieldValue(column, null)
                        }
                      : undefined
                  }
                />
              )}

              {error && <p className="text-sm text-rose-600">{error}</p>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
