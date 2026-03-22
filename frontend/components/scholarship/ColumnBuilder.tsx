"use client"

import { useEffect, useMemo, useState } from "react"
import { closestCenter, DndContext, PointerSensor, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core"
import { arrayMove, SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { FileStack, GripVertical, Sparkles } from "lucide-react"

import NizomUploader from "@/components/scholarship/NizomUploader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import EmptyState from "@/components/ui/empty-state"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import type { Column, FieldType, SuggestedColumn } from "@/types"

const FIELD_TYPE_OPTIONS: Array<{ value: FieldType; label: string }> = [
  { value: "text", label: "Text" },
  { value: "textarea", label: "Textarea" },
  { value: "file", label: "File" },
  { value: "number", label: "Number" },
  { value: "date", label: "Date" },
  { value: "select", label: "Select" },
  { value: "url", label: "URL" },
]

export type ColumnBuilderFormState = {
  name: string
  description: string
  field_type: FieldType
  select_options_text: string
  is_required: boolean
  ai_analyze: boolean
  max_score: number
  input_min: number | null
  input_max: number | null
}

type ColumnBuilderFieldErrors = Partial<Record<keyof ColumnBuilderFormState, string | undefined>>

type ColumnBuilderProps = {
  scholarshipId: string
  columns: Column[]
  importedColumns: SuggestedColumn[]
  form: ColumnBuilderFormState
  errors: ColumnBuilderFieldErrors
  formError: string | null
  onImportedColumnsChange: (columns: SuggestedColumn[]) => void
  onFieldChange: <K extends keyof ColumnBuilderFormState>(field: K, value: ColumnBuilderFormState[K]) => void
  onImportColumns: () => void
  onCreateColumn: () => void
  onDeleteColumn: (columnId: string) => void
  onReorderColumns: (order: string[]) => void
  isImportPending: boolean
  isCreatePending: boolean
  isDeletePending: boolean
  isReorderPending: boolean
}

function SortableColumnRow({
  column,
  onDeleteRequest,
  isDeletePending,
}: {
  column: Column
  onDeleteRequest: (column: Column) => void
  isDeletePending: boolean
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: column.id })

  return (
    <TableRow
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(isDragging && "relative z-10 bg-slate-50 shadow-sm")}
    >
      <TableCell>
        <div className="flex items-start gap-3">
          <button
            type="button"
            className="mt-0.5 rounded-md border border-slate-200 p-1 text-slate-500 transition hover:border-slate-300 hover:text-slate-700"
            aria-label={`${column.name} ustunini joyini o‘zgartirish`}
            {...attributes}
            {...listeners}
          >
            <GripVertical className="h-4 w-4" />
          </button>
          <div>
            <p className="font-medium text-slate-900">{column.name}</p>
            <p className="text-xs text-slate-500">{column.description || "No description"}</p>
          </div>
        </div>
      </TableCell>
      <TableCell>
        <div className="space-y-1">
          <div>{column.field_type}</div>
          {column.field_type === "number" && (column.input_min != null || column.input_max != null) && (
            <p className="text-xs text-slate-500">
              range: {column.input_min ?? "-"} - {column.input_max ?? "-"}
            </p>
          )}
        </div>
      </TableCell>
      <TableCell>{column.max_score}</TableCell>
      <TableCell>
        <div className="flex flex-wrap gap-2">
          <Badge variant={column.is_required ? "default" : "outline"}>{column.is_required ? "required" : "optional"}</Badge>
          <Badge variant={column.ai_analyze ? "secondary" : "outline"}>{column.ai_analyze ? "AI" : "manual"}</Badge>
        </div>
      </TableCell>
      <TableCell className="text-right">
        <Button type="button" variant="destructive" size="sm" onClick={() => onDeleteRequest(column)} disabled={isDeletePending}>
          O‘chirish
        </Button>
      </TableCell>
    </TableRow>
  )
}

export default function ColumnBuilder({
  scholarshipId,
  columns,
  importedColumns,
  form,
  errors,
  formError,
  onImportedColumnsChange,
  onFieldChange,
  onImportColumns,
  onCreateColumn,
  onDeleteColumn,
  onReorderColumns,
  isImportPending,
  isCreatePending,
  isDeletePending,
  isReorderPending,
}: ColumnBuilderProps) {
  const [orderedColumns, setOrderedColumns] = useState(columns)
  const [columnToDelete, setColumnToDelete] = useState<Column | null>(null)
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }))

  useEffect(() => {
    setOrderedColumns(columns)
  }, [columns])

  const orderedIds = useMemo(() => orderedColumns.map((column) => column.id), [orderedColumns])

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    if (!over || active.id === over.id) {
      return
    }

    const oldIndex = orderedColumns.findIndex((column) => column.id === active.id)
    const newIndex = orderedColumns.findIndex((column) => column.id === over.id)
    if (oldIndex === -1 || newIndex === -1) {
      return
    }

    const nextColumns = arrayMove(orderedColumns, oldIndex, newIndex).map((column, index) => ({
      ...column,
      order_index: index,
    }))
    setOrderedColumns(nextColumns)
    onReorderColumns(nextColumns.map((column) => column.id))
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-6">
        <NizomUploader scholarshipId={scholarshipId} onImportColumns={onImportedColumnsChange} />

        {importedColumns.length > 0 && (
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Sparkles className="h-4 w-4 text-amber-600" />
                AI import queue
              </CardTitle>
              <CardDescription>Tanlangan AI ustunlar shu scholarship ichiga real column sifatida qo‘shiladi.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3">
                {importedColumns.map((column) => (
                  <div key={`${column.name}-${column.order_index}`} className="rounded-2xl border border-slate-200 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-slate-900">{column.name}</p>
                      <Badge variant="outline">{column.field_type}</Badge>
                      <Badge variant={column.ai_analyze ? "secondary" : "outline"}>
                        {column.ai_analyze ? "AI analyze" : "manual"}
                      </Badge>
                    </div>
                    <p className="mt-2 text-sm text-slate-600">{column.description}</p>
                  </div>
                ))}
              </div>
              <Button type="button" onClick={onImportColumns} disabled={isImportPending}>
                {isImportPending ? "Import qilinmoqda..." : "AI ustunlarni saqlash"}
              </Button>
            </CardContent>
          </Card>
        )}

        <Card className="border-slate-200">
          <CardHeader>
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <FileStack className="h-4 w-4 text-sky-600" />
                  Current columns
                </CardTitle>
                <CardDescription>Student dynamic form aynan shu ustunlardan quriladi.</CardDescription>
              </div>
              {orderedColumns.length > 1 && (
                <Badge variant="outline">{isReorderPending ? "Tartib saqlanmoqda..." : "Drag-and-drop yoqilgan"}</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {orderedColumns.length === 0 ? (
              <EmptyState
                title="Ustunlar hali yo‘q"
                description="Student dynamic form qurilishi uchun kamida bitta baholash yoki ma’lumot ustuni qo‘shilishi kerak."
              />
            ) : (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={orderedIds} strategy={verticalListSortingStrategy}>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Flags</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {orderedColumns.map((column) => (
                        <SortableColumnRow
                          key={column.id}
                          column={column}
                          onDeleteRequest={setColumnToDelete}
                          isDeletePending={isDeletePending}
                        />
                      ))}
                    </TableBody>
                  </Table>
                </SortableContext>
              </DndContext>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle>Column Builder</CardTitle>
          <CardDescription>AI bo‘lmasa yoki qo‘shimcha mezon kerak bo‘lsa, qo‘lda ustun qo‘shing.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {formError && <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</div>}
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="column-name">
              Name
            </label>
            <Input
              id="column-name"
              value={form.name}
              aria-invalid={Boolean(errors.name)}
              onChange={(event) => onFieldChange("name", event.target.value)}
              placeholder="Masalan: Ilmiy maqolalar"
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name}</p>}
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="column-description">
              Description
            </label>
            <Textarea
              id="column-description"
              value={form.description}
              aria-invalid={Boolean(errors.description)}
              onChange={(event) => onFieldChange("description", event.target.value)}
              placeholder="Baholash talabi..."
            />
            {errors.description && <p className="mt-1 text-xs text-red-600">{errors.description}</p>}
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="column-type">
                Field type
              </label>
              <select
                id="column-type"
                className={cn("h-8 w-full rounded-lg border border-slate-300 px-2.5 text-sm", errors.field_type && "border-red-500")}
                value={form.field_type}
                onChange={(event) => onFieldChange("field_type", event.target.value as FieldType)}
              >
                {FIELD_TYPE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {errors.field_type && <p className="mt-1 text-xs text-red-600">{errors.field_type}</p>}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="column-score">
                Max score
              </label>
              <Input
                id="column-score"
                type="number"
                min={0}
                value={form.max_score}
                aria-invalid={Boolean(errors.max_score)}
                onChange={(event) => onFieldChange("max_score", Number(event.target.value) || 0)}
              />
              {errors.max_score && <p className="mt-1 text-xs text-red-600">{errors.max_score}</p>}
            </div>
          </div>

          {form.field_type === "number" && (
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="column-input-min">
                  Min value
                </label>
                <Input
                  id="column-input-min"
                  type="number"
                  step={1}
                  value={form.input_min ?? ""}
                  aria-invalid={Boolean(errors.input_min)}
                  onChange={(event) => onFieldChange("input_min", event.target.value === "" ? null : Number(event.target.value))}
                  placeholder="Masalan: 0"
                />
                {errors.input_min && <p className="mt-1 text-xs text-red-600">{errors.input_min}</p>}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="column-input-max">
                  Max value
                </label>
                <Input
                  id="column-input-max"
                  type="number"
                  step={1}
                  value={form.input_max ?? ""}
                  aria-invalid={Boolean(errors.input_max)}
                  onChange={(event) => onFieldChange("input_max", event.target.value === "" ? null : Number(event.target.value))}
                  placeholder="Masalan: 100"
                />
                {errors.input_max && <p className="mt-1 text-xs text-red-600">{errors.input_max}</p>}
              </div>
            </div>
          )}

          {form.field_type === "select" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700" htmlFor="column-options">
                Select options
              </label>
              <Input
                id="column-options"
                value={form.select_options_text}
                aria-invalid={Boolean(errors.select_options_text)}
                onChange={(event) => onFieldChange("select_options_text", event.target.value)}
                placeholder="Masalan: A, B, C"
              />
              {errors.select_options_text && <p className="mt-1 text-xs text-red-600">{errors.select_options_text}</p>}
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            <label className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm">
              <input
                type="checkbox"
                checked={form.is_required}
                onChange={(event) => onFieldChange("is_required", event.target.checked)}
              />
              Required
            </label>

            <label className="flex items-center gap-2 rounded-xl border border-slate-200 p-3 text-sm">
              <input
                type="checkbox"
                checked={form.ai_analyze}
                onChange={(event) => onFieldChange("ai_analyze", event.target.checked)}
              />
              AI analyze
            </label>
          </div>

          <Button type="button" className="w-full" onClick={onCreateColumn} disabled={isCreatePending || !form.name.trim()}>
            {isCreatePending ? "Qo‘shilmoqda..." : "Ustun qo‘shish"}
          </Button>
        </CardContent>
      </Card>

      <Dialog open={Boolean(columnToDelete)} onOpenChange={(open) => !open && setColumnToDelete(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Ustunni o‘chirish</DialogTitle>
            <DialogDescription>
              {columnToDelete ? `\`${columnToDelete.name}\` ustuni student formasi va baholashdan olib tashlanadi.` : ""}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setColumnToDelete(null)}>
              Bekor qilish
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => {
                if (columnToDelete) {
                  onDeleteColumn(columnToDelete.id)
                  setColumnToDelete(null)
                }
              }}
              disabled={isDeletePending}
            >
              {isDeletePending ? "O‘chirilmoqda..." : "Tasdiqlash"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
