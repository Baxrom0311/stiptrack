import { z } from "zod"

export type FieldErrors<T extends string> = Partial<Record<T, string>>

function optionalTrimmedString(maxLength: number, label: string) {
  return z
    .string()
    .trim()
    .max(maxLength, `${label} ${maxLength} ta belgidan oshmasligi kerak.`)
    .transform((value) => value)
}

function optionalDateString(label: string) {
  return z
    .string()
    .trim()
    .refine((value) => !value || !Number.isNaN(new Date(value).getTime()), {
      message: `${label} noto‘g‘ri formatda.`,
    })
}

export const loginFormSchema = z.object({
  email: z.string().trim().email("Email formati noto‘g‘ri."),
  password: z.string().min(1, "Parol kiritilishi shart.").max(128, "Parol juda uzun."),
})

export const registerFormSchema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(2, "F.I.Sh kamida 2 ta belgidan iborat bo‘lishi kerak.")
      .max(200, "F.I.Sh 200 ta belgidan oshmasligi kerak."),
    email: z.string().trim().email("Email formati noto‘g‘ri."),
    password: z
      .string()
      .min(8, "Parol kamida 8 ta belgidan iborat bo‘lishi kerak.")
      .max(128, "Parol 128 ta belgidan oshmasligi kerak."),
    confirm_password: z.string().min(1, "Parolni tasdiqlang.").max(128, "Parol juda uzun."),
    department: optionalTrimmedString(100, "Fakultet/bo‘lim"),
    student_id: optionalTrimmedString(50, "Student ID"),
  })
  .refine((data) => data.password === data.confirm_password, {
    path: ["confirm_password"],
    message: "Parollar mos kelmadi.",
  })

export const profileFormSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(2, "F.I.Sh kamida 2 ta belgidan iborat bo‘lishi kerak.")
    .max(200, "F.I.Sh 200 ta belgidan oshmasligi kerak."),
  department: optionalTrimmedString(100, "Fakultet/bo‘lim"),
  student_id: optionalTrimmedString(50, "Student ID"),
  is_supervisor: z.boolean(),
})

const adminUserBaseSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(2, "F.I.Sh kamida 2 ta belgidan iborat bo‘lishi kerak.")
    .max(200, "F.I.Sh 200 ta belgidan oshmasligi kerak."),
  email: z.string().trim().email("Email formati noto‘g‘ri."),
  password: z.string().max(128, "Parol 128 ta belgidan oshmasligi kerak."),
  role: z.enum(["admin", "jury", "student"]),
  department: optionalTrimmedString(100, "Fakultet/bo‘lim"),
  student_id: optionalTrimmedString(50, "Student ID"),
  is_supervisor: z.boolean(),
  is_active: z.boolean(),
})

export const adminUserCreateFormSchema = adminUserBaseSchema
  .extend({
    password: z
      .string()
      .min(8, "Parol kamida 8 ta belgidan iborat bo‘lishi kerak.")
      .max(128, "Parol 128 ta belgidan oshmasligi kerak."),
  })
  .superRefine((data, ctx) => {
    if (data.role === "student" && data.is_supervisor) {
      ctx.addIssue({
        code: "custom",
        path: ["is_supervisor"],
        message: "Student foydalanuvchi ilmiy rahbar sifatida belgilanmaydi.",
      })
    }
  })

export const adminUserUpdateFormSchema = adminUserBaseSchema.superRefine((data, ctx) => {
  if (data.password && data.password.length > 0 && data.password.length < 8) {
    ctx.addIssue({
      code: "custom",
      path: ["password"],
      message: "Parol kamida 8 ta belgidan iborat bo‘lishi kerak.",
    })
  }

  if (data.role === "student" && data.is_supervisor) {
    ctx.addIssue({
      code: "custom",
      path: ["is_supervisor"],
      message: "Student foydalanuvchi ilmiy rahbar sifatida belgilanmaydi.",
    })
  }
})

export const achievementFormSchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "Sarlavha kiritilishi shart.")
    .max(300, "Sarlavha 300 ta belgidan oshmasligi kerak."),
  type: z.enum(["none", "paper", "award", "project", "cert", "olympiad", "other"]),
  date: optionalDateString("Sana"),
  description: optionalTrimmedString(5000, "Tavsif"),
})

export const scholarshipFormSchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "Title kiritilishi shart.")
    .max(300, "Title 300 ta belgidan oshmasligi kerak."),
  description: optionalTrimmedString(5000, "Description"),
  deadline: optionalDateString("Deadline"),
  ai_analysis_enabled: z.boolean(),
  blind_review_enabled: z.boolean(),
  ai_provider: z.enum(["claude", "openai", "gemini", "ollama", "deepseek"]),
  ai_model: optionalTrimmedString(200, "AI model"),
  max_winners: z
    .number()
    .int("Butun son kiriting.")
    .min(1, "Kamida 1 ta g‘olib bo‘lishi kerak.")
    .max(100, "Max winners 100 dan oshmasligi kerak."),
})

export const scholarshipTemplateFormSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Template nomi kiritilishi shart.")
    .max(200, "Template nomi 200 ta belgidan oshmasligi kerak."),
  description: optionalTrimmedString(5000, "Description"),
})

export const scholarshipTemplateInstantiateSchema = z.object({
  template_id: z.string().uuid("Template tanlash shart."),
  title: z
    .string()
    .trim()
    .min(1, "Title kiritilishi shart.")
    .max(300, "Title 300 ta belgidan oshmasligi kerak."),
  description: optionalTrimmedString(5000, "Description"),
  deadline: optionalDateString("Deadline"),
  starts_at: optionalDateString("Template start time"),
})

export const columnFormSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, "Column nomi kiritilishi shart.")
      .max(200, "Column nomi 200 ta belgidan oshmasligi kerak."),
    description: optionalTrimmedString(5000, "Description"),
    field_type: z.enum(["text", "textarea", "file", "number", "date", "select", "url"]),
    select_options_text: z.string().trim().max(1000, "Select options juda uzun."),
    is_required: z.boolean(),
    ai_analyze: z.boolean(),
    max_score: z
      .number()
      .min(0, "Max score manfiy bo‘lishi mumkin emas.")
      .max(100, "Max score 100 dan oshmasligi kerak."),
    input_min: z.number().int("Min qiymat butun son bo‘lishi kerak.").nullable(),
    input_max: z.number().int("Max qiymat butun son bo‘lishi kerak.").nullable(),
  })
  .superRefine((data, ctx) => {
    if (data.field_type === "select") {
      const options = data.select_options_text
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)

      if (options.length === 0) {
        ctx.addIssue({
          code: "custom",
          path: ["select_options_text"],
          message: "Select turida kamida bitta option bo‘lishi kerak.",
        })
      }
    }

    if (data.field_type === "number" && data.input_min !== null && data.input_max !== null && data.input_min > data.input_max) {
      ctx.addIssue({
        code: "custom",
        path: ["input_max"],
        message: "Max qiymat min qiymatdan kichik bo‘lishi mumkin emas.",
      })
    }
  })

export const stageFormSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, "Bosqich nomi kiritilishi shart.")
      .max(150, "Bosqich nomi 150 ta belgidan oshmasligi kerak."),
    stage_type: z.enum(["application", "review", "exam", "interview", "final_decision", "appeal"]),
    description: optionalTrimmedString(5000, "Tavsif"),
    starts_at: z.string().trim().min(1, "Boshlanish sanasi kiritilishi shart."),
    ends_at: z.string().trim().min(1, "Tugash sanasi kiritilishi shart."),
    is_required: z.boolean(),
    is_active: z.boolean(),
  })
  .superRefine((data, ctx) => {
    const startsAt = new Date(data.starts_at)
    const endsAt = new Date(data.ends_at)

    if (Number.isNaN(startsAt.getTime())) {
      ctx.addIssue({
        code: "custom",
        path: ["starts_at"],
        message: "Boshlanish sanasi noto‘g‘ri.",
      })
    }

    if (Number.isNaN(endsAt.getTime())) {
      ctx.addIssue({
        code: "custom",
        path: ["ends_at"],
        message: "Tugash sanasi noto‘g‘ri.",
      })
    }

    if (!Number.isNaN(startsAt.getTime()) && !Number.isNaN(endsAt.getTime()) && endsAt <= startsAt) {
      ctx.addIssue({
        code: "custom",
        path: ["ends_at"],
        message: "Tugash sanasi boshlanish sanasidan keyin bo‘lishi kerak.",
      })
    }
  })

export const juryAssignmentSchema = z.object({
  jury_id: z.string().uuid("Hakam tanlash shart."),
})

export function getFieldErrors<T extends string>(error: z.ZodError): FieldErrors<T> {
  const fieldErrors = error.flatten().fieldErrors as Record<string, string[] | undefined>
  const result: FieldErrors<T> = {}

  for (const [field, messages] of Object.entries(fieldErrors)) {
    if (messages && messages.length > 0) {
      result[field as T] = messages[0]
    }
  }

  return result
}

export function getFirstFieldError<T extends string>(errors: FieldErrors<T>): string | null {
  for (const message of Object.values(errors)) {
    if (typeof message === "string" && message.trim().length > 0) {
      return message
    }
  }
  return null
}
