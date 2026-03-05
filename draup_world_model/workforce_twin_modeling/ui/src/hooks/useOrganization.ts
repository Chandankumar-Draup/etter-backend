import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

export function useOrg() {
  return useQuery({ queryKey: ['org'], queryFn: api.org })
}

export function useHierarchy() {
  return useQuery({ queryKey: ['hierarchy'], queryFn: api.orgHierarchy })
}

export function useFunctions() {
  return useQuery({ queryKey: ['functions'], queryFn: api.orgFunctions })
}

export function useSnapshot() {
  return useQuery({ queryKey: ['snapshot'], queryFn: api.snapshot })
}

export function useTools() {
  return useQuery({ queryKey: ['tools'], queryFn: api.orgTools })
}

export function usePresets() {
  return useQuery({ queryKey: ['presets'], queryFn: api.presets })
}

export function useRoleDetail(roleId: string | null) {
  return useQuery({
    queryKey: ['role', roleId],
    queryFn: () => api.orgRole(roleId!),
    enabled: !!roleId,
  })
}
