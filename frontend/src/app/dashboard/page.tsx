"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatCard } from "@/components/dashboard/StatCard";
import { Card } from "@/components/ui/Card";
import { LoadingState, ErrorState } from "@/components/ui/States";
import { Users, Armchair, CheckCircle2, Clock, Lock, Wrench, UserPlus } from "lucide-react";

export default function DashboardPage() {
  const summary = useQuery({ queryKey: ["dashboard", "summary"], queryFn: dashboardApi.summary });
  const projectUtil = useQuery({
    queryKey: ["dashboard", "project-utilization"],
    queryFn: dashboardApi.projectUtilization,
  });
  const floorUtil = useQuery({
    queryKey: ["dashboard", "floor-utilization"],
    queryFn: dashboardApi.floorUtilization,
  });
  const recent = useQuery({
    queryKey: ["dashboard", "recent-allocations"],
    queryFn: () => dashboardApi.recentAllocations(10),
  });

  return (
    <>
      <PageHeader title="Dashboard" description="Live seat & project utilization across Ethara" />
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
        {summary.isLoading && <LoadingState label="Loading dashboard..." />}
        {summary.isError && <ErrorState message="Could not load dashboard summary." />}

        {summary.data && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <StatCard label="Total Employees" value={summary.data.total_employees} icon={Users} tone="blue" />
            <StatCard label="Total Seats" value={summary.data.total_seats} icon={Armchair} tone="neutral" />
            <StatCard label="Occupied Seats" value={summary.data.occupied_seats} icon={CheckCircle2} tone="blue" />
            <StatCard label="Available Seats" value={summary.data.available_seats} icon={Armchair} tone="emerald" />
            <StatCard label="Reserved Seats" value={summary.data.reserved_seats} icon={Lock} tone="amber" />
            <StatCard label="Maintenance" value={summary.data.maintenance_seats} icon={Wrench} tone="zinc" />
            <StatCard label="Pending Allocation" value={summary.data.pending_allocation} icon={UserPlus} tone="amber" />
            <StatCard label="Active Employees" value={summary.data.active_employees} icon={Clock} tone="neutral" />
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card className="p-4">
            <h2 className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-50">
              Project-wise Seat Allocation
            </h2>
            {projectUtil.isLoading && <LoadingState />}
            {projectUtil.data && (
              <div className="space-y-3">
                {projectUtil.data.map((p) => (
                  <div key={p.project_id}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">{p.project_name}</span>
                      <span className="text-zinc-400">
                        {p.allocated_seats}/{p.employee_count} ({p.utilization_pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-zinc-100 dark:bg-zinc-800">
                      <div
                        className="h-2 rounded-full bg-zinc-900 dark:bg-zinc-100"
                        style={{ width: `${Math.min(p.utilization_pct, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="p-4">
            <h2 className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-50">Floor-wise Occupancy</h2>
            {floorUtil.isLoading && <LoadingState />}
            {floorUtil.data && (
              <div className="space-y-3">
                {floorUtil.data.map((f) => (
                  <div key={f.floor}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-zinc-700 dark:text-zinc-300">Floor {f.floor}</span>
                      <span className="text-zinc-400">
                        {f.occupied_seats}/{f.total_seats} occupied ({f.occupancy_pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-zinc-100 dark:bg-zinc-800">
                      <div
                        className="h-2 rounded-full bg-blue-600"
                        style={{ width: `${Math.min(f.occupancy_pct, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <Card className="p-4">
          <h2 className="mb-3 text-sm font-semibold text-zinc-900 dark:text-zinc-50">Recent Allocations</h2>
          {recent.isLoading && <LoadingState />}
          {recent.data && recent.data.length === 0 && (
            <p className="text-sm text-zinc-400">No allocation activity yet.</p>
          )}
          {recent.data && recent.data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-zinc-400 border-b border-zinc-100 dark:border-zinc-800">
                    <th className="pb-2 font-medium">Employee</th>
                    <th className="pb-2 font-medium">Seat</th>
                    <th className="pb-2 font-medium">Project</th>
                    <th className="pb-2 font-medium">Action</th>
                    <th className="pb-2 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                  {recent.data.map((r, i) => (
                    <tr key={i}>
                      <td className="py-2 text-zinc-800 dark:text-zinc-200">{r.employee_name}</td>
                      <td className="py-2 font-mono text-xs text-zinc-500">{r.seat_code}</td>
                      <td className="py-2 text-zinc-500">{r.project_name ?? "—"}</td>
                      <td className="py-2 capitalize text-zinc-500">{r.action}</td>
                      <td className="py-2 text-zinc-400 text-xs">
                        {new Date(r.allocation_date).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
