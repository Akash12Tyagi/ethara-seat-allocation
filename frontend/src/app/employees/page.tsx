"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { employeesApi, projectsApi, seatsApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import { EmployeeFormModal } from "@/components/employees/EmployeeFormModal";
import { AllocateSeatModal } from "@/components/employees/AllocateSeatModal";
import { Plus, Search, UserMinus, Armchair, Pencil } from "lucide-react";
import type { Employee } from "@/lib/types";

const PAGE_SIZE = 20;

export default function EmployeesPage() {
  return (
    <Suspense fallback={<div className="flex-1" />}>
      <EmployeesPageContent />
    </Suspense>
  );
}

function EmployeesPageContent() {
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const [search, setSearch] = useState("");
  const [projectId, setProjectId] = useState(searchParams.get("project_id") ?? "");
  const [seatStatus, setSeatStatus] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  const [formOpen, setFormOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [allocatingEmployee, setAllocatingEmployee] = useState<Employee | null>(null);

  const projects = useQuery({ queryKey: ["projects"], queryFn: projectsApi.list });

  const params = useMemo(
    () => ({
      search: search || undefined,
      project_id: projectId ? Number(projectId) : undefined,
      seat_status: seatStatus || undefined,
      status: statusFilter || undefined,
      page,
      page_size: PAGE_SIZE,
    }),
    [search, projectId, seatStatus, statusFilter, page]
  );

  const employees = useQuery({
    queryKey: ["employees", params],
    queryFn: () => employeesApi.list(params),
  });

  const releaseMutation = useMutation({
    mutationFn: (employeeId: number) => seatsApi.release({ employee_id: employeeId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["seats"] });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (employeeId: number) => employeesApi.deactivate(employeeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  function resetFiltersAndSearch(fn: () => void) {
    fn();
    setPage(1);
  }

  return (
    <>
      <PageHeader
        title="Employees"
        description={employees.data ? `${employees.data.total.toLocaleString()} total` : undefined}
        actions={
          <Button
            onClick={() => {
              setEditingEmployee(null);
              setFormOpen(true);
            }}
          >
            <Plus size={15} /> Add Employee
          </Button>
        }
      />

      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        <Card className="p-3">
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
              <Input
                placeholder="Search name, ID, or email..."
                className="pl-8"
                value={search}
                onChange={(e) => resetFiltersAndSearch(() => setSearch(e.target.value))}
              />
            </div>
            <Select
              className="w-auto min-w-[160px]"
              value={projectId}
              onChange={(e) => resetFiltersAndSearch(() => setProjectId(e.target.value))}
            >
              <option value="">All projects</option>
              {projects.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
            <Select
              className="w-auto min-w-[160px]"
              value={seatStatus}
              onChange={(e) => resetFiltersAndSearch(() => setSeatStatus(e.target.value))}
            >
              <option value="">Any seat status</option>
              <option value="allocated">Allocated</option>
              <option value="pending">Pending allocation</option>
            </Select>
            <Select
              className="w-auto min-w-[150px]"
              value={statusFilter}
              onChange={(e) => resetFiltersAndSearch(() => setStatusFilter(e.target.value))}
            >
              <option value="">Any employment status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </Select>
          </div>
        </Card>

        <Card>
          {employees.isLoading && <LoadingState label="Loading employees..." />}
          {employees.isError && <ErrorState message="Could not load employees." />}
          {employees.data && employees.data.items.length === 0 && (
            <EmptyState title="No employees match these filters" description="Try adjusting your search or filters." />
          )}

          {employees.data && employees.data.items.length > 0 && (
            <>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-zinc-400 border-b border-zinc-100 dark:border-zinc-800">
                      <th className="px-4 py-2.5 font-medium">Employee</th>
                      <th className="px-4 py-2.5 font-medium">Project</th>
                      <th className="px-4 py-2.5 font-medium">Department / Role</th>
                      <th className="px-4 py-2.5 font-medium">Seat</th>
                      <th className="px-4 py-2.5 font-medium">Status</th>
                      <th className="px-4 py-2.5 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                    {employees.data.items.map((emp) => (
                      <tr key={emp.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/50">
                        <td className="px-4 py-3">
                          <p className="font-medium text-zinc-900 dark:text-zinc-50">{emp.name}</p>
                          <p className="text-xs text-zinc-400">
                            {emp.employee_code} · {emp.email}
                          </p>
                        </td>
                        <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">
                          {emp.project_name ?? <span className="text-zinc-400">Unassigned</span>}
                        </td>
                        <td className="px-4 py-3 text-zinc-600 dark:text-zinc-300">
                          {emp.department}
                          <br />
                          <span className="text-xs text-zinc-400">{emp.role}</span>
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-zinc-500">
                          {emp.seat ? emp.seat.code : "—"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-col gap-1">
                            <Badge variant={emp.status === "active" ? "active" : "inactive"}>{emp.status}</Badge>
                            <Badge variant={emp.seat_allocation_status === "allocated" ? "allocated" : "pending"}>
                              {emp.seat_allocation_status}
                            </Badge>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-1">
                            <button
                              title="Edit"
                              onClick={() => {
                                setEditingEmployee(emp);
                                setFormOpen(true);
                              }}
                              className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800"
                            >
                              <Pencil size={14} />
                            </button>
                            {emp.seat_allocation_status === "pending" ? (
                              <button
                                title="Allocate seat"
                                onClick={() => setAllocatingEmployee(emp)}
                                disabled={emp.status !== "active"}
                                className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-emerald-600 disabled:opacity-40 dark:hover:bg-zinc-800"
                              >
                                <Armchair size={14} />
                              </button>
                            ) : (
                              <button
                                title="Release seat"
                                onClick={() => releaseMutation.mutate(emp.id)}
                                className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-amber-600 dark:hover:bg-zinc-800"
                              >
                                <Armchair size={14} />
                              </button>
                            )}
                            <button
                              title="Deactivate"
                              onClick={() => deactivateMutation.mutate(emp.id)}
                              disabled={emp.status === "inactive"}
                              className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-red-600 disabled:opacity-40 dark:hover:bg-zinc-800"
                            >
                              <UserMinus size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center justify-between border-t border-zinc-100 px-4 py-3 dark:border-zinc-800">
                <p className="text-xs text-zinc-400">
                  Page {employees.data.page} of {employees.data.total_pages} · {employees.data.total.toLocaleString()}{" "}
                  employees
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Previous
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={page >= employees.data.total_pages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>

      <EmployeeFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        employee={editingEmployee}
      />
      <AllocateSeatModal
        open={Boolean(allocatingEmployee)}
        onClose={() => setAllocatingEmployee(null)}
        employee={allocatingEmployee}
      />
    </>
  );
}
