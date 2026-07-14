import type {
  AIQueryResponse,
  DashboardSummary,
  Employee,
  FloorUtilization,
  Paginated,
  Project,
  ProjectUtilization,
  RecentAllocation,
  Seat,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail ?? message;
    } catch {
      // response wasn't JSON, keep default message
    }
    throw new ApiRequestError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function qs(params: object): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params as Record<string, unknown>)) {
    if (v !== undefined && v !== null && v !== "") usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}

// ---- Employees ----
export interface EmployeeListParams {
  search?: string;
  project_id?: number;
  department?: string;
  status?: string;
  seat_status?: string;
  page?: number;
  page_size?: number;
}

export const employeesApi = {
  list: (params: EmployeeListParams = {}) =>
    request<Paginated<Employee>>(`/employees${qs(params)}`),
  get: (id: number) => request<Employee>(`/employees/${id}`),
  create: (payload: Record<string, unknown>) =>
    request<Employee>("/employees", { method: "POST", body: JSON.stringify(payload) }),
  update: (id: number, payload: Record<string, unknown>) =>
    request<Employee>(`/employees/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deactivate: (id: number) => request<{ message: string }>(`/employees/${id}`, { method: "DELETE" }),
  pendingAllocation: (limit = 100) =>
    request<Employee[]>(`/employees/pending-allocation${qs({ limit })}`),
};

// ---- Projects ----
export const projectsApi = {
  list: () => request<Project[]>("/projects"),
  create: (payload: Record<string, unknown>) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  employees: (id: number) => request<Employee[]>(`/projects/${id}/employees`),
};

// ---- Seats ----
export interface SeatListParams {
  floor?: number;
  zone?: string;
  status?: string;
  project_id?: number;
  page?: number;
  page_size?: number;
}

export const seatsApi = {
  list: (params: SeatListParams = {}) => request<Paginated<Seat>>(`/seats${qs(params)}`),
  available: (params: { floor?: number; zone?: string; limit?: number } = {}) =>
    request<Seat[]>(`/seats/available${qs(params)}`),
  create: (payload: Record<string, unknown>) =>
    request<Seat>("/seats", { method: "POST", body: JSON.stringify(payload) }),
  allocate: (payload: {
    employee_id: number;
    seat_id?: number;
    preferred_floor?: number;
    preferred_zone?: string;
  }) =>
    request<{ seat: Seat; message: string; alternate_zone_used: boolean }>("/seats/allocate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  release: (payload: { employee_id?: number; seat_id?: number }) =>
    request<Seat>("/seats/release", { method: "POST", body: JSON.stringify(payload) }),
};

// ---- Dashboard ----
export const dashboardApi = {
  summary: () => request<DashboardSummary>("/dashboard/summary"),
  projectUtilization: () => request<ProjectUtilization[]>("/dashboard/project-utilization"),
  floorUtilization: () => request<FloorUtilization[]>("/dashboard/floor-utilization"),
  recentAllocations: (limit = 20) =>
    request<RecentAllocation[]>(`/dashboard/recent-allocations${qs({ limit })}`),
};

// ---- AI ----
export const aiApi = {
  query: (query: string, employee_email?: string) =>
    request<AIQueryResponse>("/ai/query", {
      method: "POST",
      body: JSON.stringify({ query, employee_email }),
    }),
};
