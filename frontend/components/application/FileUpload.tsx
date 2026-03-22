"use client"
/* eslint-disable @next/next/no-img-element */

import { FileText, ImageIcon, Loader2, Trash2, UploadCloud } from "lucide-react"
import { useCallback, useMemo, useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  formatFileSizeLimit,
  getFileValidationRule,
  type FileValidationKind,
  validateSelectedFile,
} from "@/lib/file-validation"

type FileUploadProps = {
  kind?: FileValidationKind
  value?: string | null
  disabled?: boolean
  onUpload: (file: File, onProgress: (progress: number) => void) => Promise<void>
  onDelete?: () => Promise<void> | void
}

function fileNameFromUrl(url: string): string {
  const raw = url.split("?")[0]?.split("#")[0] ?? url
  const part = raw.split("/").pop() ?? raw
  try {
    return decodeURIComponent(part)
  } catch {
    return part
  }
}

function isImageFile(url: string): boolean {
  const normalized = url.toLowerCase()
  return normalized.endsWith(".jpg") || normalized.endsWith(".jpeg") || normalized.endsWith(".png") || normalized.endsWith(".webp")
}

export default function FileUpload({ kind = "application", value, disabled, onUpload, onDelete }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isBusy, setIsBusy] = useState(false)

  const rule = useMemo(() => getFileValidationRule(kind), [kind])

  const handleUpload = useCallback(
    async (file: File) => {
      const validationMessage = validateSelectedFile(file, kind)
      if (validationMessage) {
        setError(validationMessage)
        return
      }

      setError(null)
      setProgress(0)
      setIsBusy(true)

      try {
        await onUpload(file, setProgress)
        setProgress(100)
      } catch (uploadError) {
        setProgress(0)
        setError(uploadError instanceof Error ? uploadError.message : "Faylni yuklab bo‘lmadi.")
      } finally {
        setIsBusy(false)
        if (inputRef.current) {
          inputRef.current.value = ""
        }
      }
    },
    [kind, onUpload],
  )

  const handleFileList = useCallback(
    async (files: FileList | null) => {
      const file = files?.[0]
      if (!file) {
        return
      }
      await handleUpload(file)
    },
    [handleUpload],
  )

  const handleDelete = useCallback(async () => {
    if (!onDelete) {
      return
    }

    setError(null)
    setProgress(0)
    setIsBusy(true)
    try {
      await onDelete()
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Faylni o‘chirib bo‘lmadi.")
    } finally {
      setIsBusy(false)
    }
  }, [onDelete])

  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        onClick={() => {
          if (!disabled) {
            inputRef.current?.click()
          }
        }}
        onKeyDown={(event) => {
          if (!disabled && (event.key === "Enter" || event.key === " ")) {
            event.preventDefault()
            inputRef.current?.click()
          }
        }}
        onDragEnter={(event) => {
          event.preventDefault()
          if (!disabled) {
            setDragActive(true)
          }
        }}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) {
            setDragActive(true)
          }
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
            return
          }
          setDragActive(false)
        }}
        onDrop={async (event) => {
          event.preventDefault()
          setDragActive(false)
          if (disabled) {
            return
          }
          await handleFileList(event.dataTransfer.files)
        }}
        className={cn(
          "rounded-2xl border border-dashed p-4 transition-colors",
          disabled ? "cursor-not-allowed bg-slate-50 opacity-70" : "cursor-pointer bg-slate-50 hover:bg-slate-100",
          dragActive && "border-sky-400 bg-sky-50",
          error && "border-rose-300 bg-rose-50",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={rule.accept}
          className="hidden"
          disabled={disabled || isBusy}
          onChange={async (event) => {
            await handleFileList(event.target.files)
          }}
        />
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
              <UploadCloud className="h-4 w-4 text-sky-700" />
              Faylni shu yerga tashlang yoki tanlang
            </div>
            <p className="text-xs text-slate-500">
              Ruxsat etilgan formatlar: {rule.allowedExtensions.map((item) => `.${item}`).join(", ")} | Limit: {formatFileSizeLimit(rule.maxSizeBytes)}
            </p>
          </div>
          <Button type="button" variant="outline" size="sm" disabled={disabled || isBusy}>
            Fayl tanlash
          </Button>
        </div>
      </div>

      {(isBusy || progress > 0) && (
        <div className="space-y-1">
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-sky-600 transition-all" style={{ width: `${progress}%` }} />
          </div>
          <p className="text-xs text-slate-500">{isBusy ? `Yuklanmoqda... ${progress}%` : "Yuklash tugadi"}</p>
        </div>
      )}

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {value && (
        <div className="rounded-2xl border border-slate-200 bg-white p-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              {isImageFile(value) ? (
                <img src={value} alt="Uploaded preview" className="h-16 w-16 rounded-xl object-cover" />
              ) : (
                <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-slate-100">
                  {value.toLowerCase().endsWith(".pdf") ? (
                    <FileText className="h-6 w-6 text-slate-700" />
                  ) : (
                    <ImageIcon className="h-6 w-6 text-slate-700" />
                  )}
                </div>
              )}
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-900">{fileNameFromUrl(value)}</p>
                <a
                  href={value}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-sky-700 underline underline-offset-2"
                >
                  Faylni ochish
                </a>
              </div>
            </div>
            {onDelete && (
              <Button type="button" variant="destructive" size="sm" disabled={disabled || isBusy} onClick={handleDelete}>
                {isBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                O‘chirish
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
