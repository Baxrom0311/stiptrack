"use client"

import { useQuery } from "@tanstack/react-query"

import { getApplication, listMyApplications, listScholarshipApplications } from "@/lib/applications"
import type { ApplicationStatus } from "@/types"

type UseApplicationsParams = {
  scholarshipId?: string
  status?: ApplicationStatus
  skip?: number
  limit?: number
  enabled?: boolean
}

export function useApplications({ scholarshipId, enabled = true, ...params }: UseApplicationsParams) {
  return useQuery({
    queryKey: ["applications", scholarshipId, params],
    queryFn: () => listScholarshipApplications(scholarshipId as string, params),
    enabled: Boolean(scholarshipId) && enabled,
    retry: 0,
  })
}

export function useApplication(applicationId?: string, enabled = true) {
  return useQuery({
    queryKey: ["application", applicationId],
    queryFn: () => getApplication(applicationId as string),
    enabled: Boolean(applicationId) && enabled,
    retry: 0,
  })
}

export function useMyApplications(enabled = true) {
  return useQuery({
    queryKey: ["my-applications"],
    queryFn: listMyApplications,
    enabled,
    retry: 0,
  })
}
