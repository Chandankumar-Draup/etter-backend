/**
 * API Client — typed fetch wrappers for all backend endpoints.
 */
const BASE = '/api'

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`)
  return res.json()
}

function post<T>(path: string, body: unknown): Promise<T> {
  return fetchJSON<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

// ─── Organization ───
export const api = {
  health: () => fetchJSON<{ status: string; roles: number; functions: string[] }>('/health'),
  org: () => fetchJSON<any>('/org'),
  orgHierarchy: () => fetchJSON<any>('/org/hierarchy'),
  orgFunctions: () => fetchJSON<any[]>('/org/functions'),
  orgRole: (id: string) => fetchJSON<any>(`/org/roles/${id}`),
  orgTools: () => fetchJSON<any[]>('/org/tools'),

  // ─── Snapshot ───
  snapshot: () => fetchJSON<any>('/snapshot'),
  snapshotFunction: (name: string) => fetchJSON<any>(`/snapshot/function/${encodeURIComponent(name)}`),
  snapshotRole: (id: string) => fetchJSON<any>(`/snapshot/role/${id}`),
  opportunities: () => fetchJSON<any>('/snapshot/opportunities'),

  // ─── Cascade ───
  cascade: (config: {
    stimulus_name?: string
    tools?: string[]
    target_functions?: string[]
    policy?: string
    absorption_factor?: number
    alpha?: number
  }) => post<any>('/cascade', config),

  // ─── Simulation ───
  simulate: (config: any) => post<any>('/simulate', config),
  simulatePreset: (id: string, trace = false) =>
    post<any>(`/simulate/preset/${id}?trace=${trace}`, {}),
  presets: () => fetchJSON<any[]>('/simulate/presets'),

  // ─── Scenarios ───
  catalog: () => fetchJSON<{ total: number; scenarios: any[] }>('/scenarios/catalog'),
  runScenarios: (ids?: string[], families?: string[]) =>
    post<any>('/scenarios/run', { scenario_ids: ids, families }),
  runSingleScenario: (id: string, trace = false) =>
    post<any>(`/scenarios/run-single/${id}?trace=${trace}`, {}),

  // ─── Compare ───
  compare: (scenarios: any[], trace = false) =>
    post<any>('/compare', { scenarios, trace }),
}
