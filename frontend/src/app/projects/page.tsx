"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { projectsApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { LoadingState, ErrorState } from "@/components/ui/States";
import { ProjectFormModal } from "@/components/projects/ProjectFormModal";
import { Plus, FolderKanban } from "lucide-react";

export default function ProjectsPage() {
  const [formOpen, setFormOpen] = useState(false);
  const projects = useQuery({ queryKey: ["projects"], queryFn: projectsApi.list });

  return (
    <>
      <PageHeader
        title="Projects"
        description={projects.data ? `${projects.data.length} projects` : undefined}
        actions={
          <Button onClick={() => setFormOpen(true)}>
            <Plus size={15} /> New Project
          </Button>
        }
      />

      <div className="flex-1 overflow-y-auto p-4 sm:p-6">
        {projects.isLoading && <LoadingState label="Loading projects..." />}
        {projects.isError && <ErrorState message="Could not load projects." />}

        {projects.data && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.data.map((p) => (
              <Card key={p.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-100 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">
                    <FolderKanban size={17} />
                  </div>
                  <Badge variant={p.status === "active" ? "active" : "inactive"}>{p.status}</Badge>
                </div>
                <h3 className="mt-3 text-sm font-semibold text-zinc-900 dark:text-zinc-50">{p.name}</h3>
                {p.manager_name && <p className="text-xs text-zinc-400">Manager: {p.manager_name}</p>}
                {p.description && <p className="mt-1 text-xs text-zinc-500">{p.description}</p>}
                <div className="mt-3 flex items-center justify-between border-t border-zinc-100 pt-3 text-xs dark:border-zinc-800">
                  <span className="text-zinc-500">
                    <span className="font-semibold text-zinc-900 dark:text-zinc-50">{p.employee_count}</span>{" "}
                    employees
                  </span>
                  <a href={`/employees?project_id=${p.id}`} className="font-medium text-zinc-600 hover:underline dark:text-zinc-300">
                    View team →
                  </a>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <ProjectFormModal open={formOpen} onClose={() => setFormOpen(false)} />
    </>
  );
}
