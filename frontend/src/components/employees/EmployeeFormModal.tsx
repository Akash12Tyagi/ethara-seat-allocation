"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { employeesApi, projectsApi, ApiRequestError } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Input, Label, Select } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useState } from "react";
import type { Employee } from "@/lib/types";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Enter a valid email"),
  department: z.string().min(1, "Department is required"),
  role: z.string().min(1, "Role is required"),
  joining_date: z.string().min(1, "Joining date is required"),
  project_id: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export function EmployeeFormModal({
  open,
  onClose,
  employee,
}: {
  open: boolean;
  onClose: () => void;
  employee?: Employee | null;
}) {
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const isEdit = Boolean(employee);

  const projects = useQuery({ queryKey: ["projects"], queryFn: projectsApi.list });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: employee
      ? {
          name: employee.name,
          email: employee.email,
          department: employee.department,
          role: employee.role,
          joining_date: employee.joining_date,
          project_id: employee.project_id ? String(employee.project_id) : "",
        }
      : undefined,
  });

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        ...values,
        project_id: values.project_id ? Number(values.project_id) : null,
      };
      if (isEdit && employee) {
        return employeesApi.update(employee.id, payload);
      }
      return employeesApi.create(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      reset();
      onClose();
    },
    onError: (err: unknown) => {
      setServerError(err instanceof ApiRequestError ? err.message : "Something went wrong");
    },
  });

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? "Edit Employee" : "Add Employee"}>
      <form
        onSubmit={handleSubmit((values) => {
          setServerError(null);
          mutation.mutate(values);
        })}
        className="space-y-3"
      >
        <div>
          <Label>Full name</Label>
          <Input placeholder="e.g. Amit Sharma" {...register("name")} />
          {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
        </div>
        <div>
          <Label>Email</Label>
          <Input type="email" placeholder="amit@ethara.ai" {...register("email")} />
          {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Department</Label>
            <Input placeholder="Engineering" {...register("department")} />
            {errors.department && <p className="mt-1 text-xs text-red-500">{errors.department.message}</p>}
          </div>
          <div>
            <Label>Role</Label>
            <Input placeholder="SDE2" {...register("role")} />
            {errors.role && <p className="mt-1 text-xs text-red-500">{errors.role.message}</p>}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Joining date</Label>
            <Input type="date" {...register("joining_date")} />
            {errors.joining_date && <p className="mt-1 text-xs text-red-500">{errors.joining_date.message}</p>}
          </div>
          <div>
            <Label>Project</Label>
            <Select {...register("project_id")}>
              <option value="">Unassigned</option>
              {projects.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          </div>
        </div>

        {serverError && <p className="text-xs text-red-500">{serverError}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting || mutation.isPending}>
            {isEdit ? "Save changes" : "Create employee"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
