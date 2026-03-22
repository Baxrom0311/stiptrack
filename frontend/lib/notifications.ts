"use client"

import { AxiosError } from "axios"
import { toast } from "sonner"

type ApiErrorDetail = {
  detail?: string | { message?: string }
}

export function extractErrorMessage(error: unknown, fallback = "Xatolik yuz berdi."): string {
  if (error instanceof Error && !(error as AxiosError).response) {
    return error.message || fallback
  }

  const axiosError = error as AxiosError<ApiErrorDetail>
  const detail = axiosError.response?.data?.detail
  if (typeof detail === "string" && detail.trim()) {
    return detail
  }
  if (detail && typeof detail === "object" && typeof detail.message === "string" && detail.message.trim()) {
    return detail.message
  }

  return fallback
}

export function notifySuccess(message: string) {
  toast.success(message)
}

export function notifyWarning(message: string) {
  toast.warning(message)
}

export function notifyError(error: unknown, fallback?: string) {
  const message = extractErrorMessage(error, fallback)
  toast.error(message)
  return message
}
