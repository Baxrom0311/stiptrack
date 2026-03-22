"use client"

import { useQuery } from "@tanstack/react-query"

import {
  getScholarship,
  listScholarshipColumns,
  listScholarships,
  type ListScholarshipsParams,
} from "@/lib/scholarships"

export function useScholarships(params: ListScholarshipsParams = {}, enabled = true) {
  return useQuery({
    queryKey: ["scholarships", params],
    queryFn: () => listScholarships(params),
    enabled,
    retry: 0,
  })
}

export function useScholarship(scholarshipId?: string, enabled = true) {
  return useQuery({
    queryKey: ["scholarship", scholarshipId],
    queryFn: () => getScholarship(scholarshipId as string),
    enabled: Boolean(scholarshipId) && enabled,
    retry: 0,
  })
}

export function useScholarshipColumns(scholarshipId?: string, enabled = true) {
  return useQuery({
    queryKey: ["scholarship-columns", scholarshipId],
    queryFn: () => listScholarshipColumns(scholarshipId as string),
    enabled: Boolean(scholarshipId) && enabled,
    retry: 0,
  })
}
