export type EmploymentStatus = "active" | "inactive";
export type ProjectStatus = "active" | "inactive";
export type SeatStatus = "available" | "occupied" | "reserved" | "maintenance";
export type SeatAllocationDisplayStatus = "allocated" | "pending";

export interface Project {
  id: number;
  name: string;
  description: string | null;
  manager_name: string | null;
  status: ProjectStatus;
  created_at: string;
  employee_count: number;
}

export interface SeatSummary {
  id: number;
  floor: number;
  zone: string;
  bay: string;
  seat_number: string;
  code: string;
}

export interface Employee {
  id: number;
  employee_code: string;
  name: string;
  email: string;
  department: string;
  role: string;
  joining_date: string;
  status: EmploymentStatus;
  project_id: number | null;
  project_name: string | null;
  seat: SeatSummary | null;
  seat_allocation_status: SeatAllocationDisplayStatus;
  created_at: string;
  updated_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Seat {
  id: number;
  floor: number;
  zone: string;
  bay: string;
  seat_number: string;
  status: SeatStatus;
  code: string;
  allocated_employee_id: number | null;
  allocated_employee_name: string | null;
  allocated_project_id: number | null;
  allocated_project_name: string | null;
  allocation_date: string | null;
}

export interface DashboardSummary {
  total_employees: number;
  active_employees: number;
  total_seats: number;
  occupied_seats: number;
  available_seats: number;
  reserved_seats: number;
  maintenance_seats: number;
  pending_allocation: number;
}

export interface ProjectUtilization {
  project_id: number;
  project_name: string;
  employee_count: number;
  allocated_seats: number;
  utilization_pct: number;
}

export interface FloorUtilization {
  floor: number;
  total_seats: number;
  occupied_seats: number;
  available_seats: number;
  reserved_seats: number;
  maintenance_seats: number;
  occupancy_pct: number;
}

export interface RecentAllocation {
  employee_name: string;
  seat_code: string;
  project_name: string | null;
  allocation_date: string;
  action: "allocated" | "released";
}

export interface AIQueryResponse {
  answer: string;
  intent: string;
  data: Record<string, unknown> | null;
}

export interface ApiError {
  detail: string;
}
