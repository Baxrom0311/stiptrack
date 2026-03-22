export type FileValidationKind = "nizom" | "achievement" | "application" | "appeal"

type FileValidationRule = {
  label: string
  accept: string
  maxSizeBytes: number
  allowedMimeTypes: string[]
  allowedExtensions: string[]
}

const MB = 1024 * 1024

const DEFAULT_FILE_RULE: FileValidationRule = {
  label: "Fayl",
  accept: ".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx",
  maxSizeBytes: 20 * MB,
  allowedMimeTypes: [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ],
  allowedExtensions: ["pdf", "jpg", "jpeg", "png", "webp", "doc", "docx"],
}

const FILE_VALIDATION_RULES: Record<FileValidationKind, FileValidationRule> = {
  nizom: {
    label: "Nizom fayli",
    accept: ".pdf,application/pdf",
    maxSizeBytes: 10 * MB,
    allowedMimeTypes: ["application/pdf"],
    allowedExtensions: ["pdf"],
  },
  achievement: {
    label: "Yutuq fayli",
    accept: ".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp",
    maxSizeBytes: 10 * MB,
    allowedMimeTypes: ["application/pdf", "image/jpeg", "image/png", "image/webp"],
    allowedExtensions: ["pdf", "jpg", "jpeg", "png", "webp"],
  },
  application: DEFAULT_FILE_RULE,
  appeal: {
    ...DEFAULT_FILE_RULE,
    label: "Apellyatsiya fayli",
    maxSizeBytes: 10 * MB,
  },
}

function getFileExtension(filename: string): string {
  const normalized = filename.trim().toLowerCase()
  if (!normalized.includes(".")) {
    return ""
  }
  return normalized.split(".").pop() ?? ""
}

function formatAllowedExtensions(rule: FileValidationRule): string {
  return rule.allowedExtensions.map((extension) => `.${extension}`).join(", ")
}

export function getFileValidationRule(kind: FileValidationKind): FileValidationRule {
  return FILE_VALIDATION_RULES[kind]
}

export function formatFileSizeLimit(maxSizeBytes: number): string {
  return `${Math.round(maxSizeBytes / MB)} MB`
}

export function validateSelectedFile(file: File, kind: FileValidationKind): string | null {
  const rule = getFileValidationRule(kind)
  const extension = getFileExtension(file.name)
  const mimeType = file.type.toLowerCase()

  if (file.size === 0) {
    return "Bo'sh fayl tanlab bo'lmaydi."
  }

  if (file.size > rule.maxSizeBytes) {
    return `${rule.label} hajmi ${formatFileSizeLimit(rule.maxSizeBytes)} dan oshmasligi kerak.`
  }

  if (!rule.allowedExtensions.includes(extension)) {
    return `${rule.label} uchun faqat ${formatAllowedExtensions(rule)} formatlari qabul qilinadi.`
  }

  if (mimeType && !rule.allowedMimeTypes.includes(mimeType)) {
    return `${rule.label} turi mos emas. Faqat ${formatAllowedExtensions(rule)} formatlari qabul qilinadi.`
  }

  return null
}
