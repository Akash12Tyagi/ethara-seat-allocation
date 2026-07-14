"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { projectsApi, ApiRequestError } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Input, Label } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useState } from "react";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  description: z.string().optional(),
  manager_name: z.string().optional(),
});
type FormValues = z.infer<typeof schema>;

export function ProjectFormModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => projectsApi.create(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      reset();
      onClose();
    },
    onError: (err: unknown) => {
      setServerError(err instanceof ApiRequestError ? err.message : "Something went wrong");
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="New Project">
      <form
        onSubmit={handleSubmit((values) => {
          setServerError(null);
          mutation.mutate(values);
        })}
        className="space-y-3"
      >
        <div>
          <Label>Project name</Label>
          <Input placeholder="e.g. Talos" {...register("name")} />
          {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
        </div>
        <div>
          <Label>Manager</Label>
          <Input placeholder="Manager name" {...register("manager_name")} />
        </div>
        <div>
          <Label>Description</Label>
          <Input placeholder="Optional description" {...register("description")} />
        </div>
        {serverError && <p className="text-xs text-red-500">{serverError}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting || mutation.isPending}>
            Create project
          </Button>
        </div>
      </form>
    </Modal>
  );
}
