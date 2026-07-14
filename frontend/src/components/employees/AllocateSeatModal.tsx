"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { seatsApi, ApiRequestError } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Input, Label } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import type { Employee } from "@/lib/types";

export function AllocateSeatModal({
  open,
  onClose,
  employee,
}: {
  open: boolean;
  onClose: () => void;
  employee: Employee | null;
}) {
  const queryClient = useQueryClient();
  const [floor, setFloor] = useState("");
  const [zone, setZone] = useState("");
  const [result, setResult] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      seatsApi.allocate({
        employee_id: employee!.id,
        preferred_floor: floor ? Number(floor) : undefined,
        preferred_zone: zone || undefined,
      }),
    onSuccess: (data) => {
      setResult(data.message);
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["seats"] });
    },
  });

  const handleClose = () => {
    setResult(null);
    setFloor("");
    setZone("");
    mutation.reset();
    onClose();
  };

  if (!employee) return null;

  return (
    <Modal open={open} onClose={handleClose} title={`Allocate a seat for ${employee.name}`}>
      <div className="space-y-3">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Leave floor/zone blank to let the engine auto-select the best seat near this employee&apos;s
          project team.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label>Preferred floor (optional)</Label>
            <Input type="number" min={1} value={floor} onChange={(e) => setFloor(e.target.value)} />
          </div>
          <div>
            <Label>Preferred zone (optional)</Label>
            <Input value={zone} onChange={(e) => setZone(e.target.value.toUpperCase())} maxLength={2} />
          </div>
        </div>

        {mutation.isError && (
          <p className="text-xs text-red-500">
            {mutation.error instanceof ApiRequestError ? mutation.error.message : "Allocation failed"}
          </p>
        )}
        {result && <p className="text-xs text-emerald-600 dark:text-emerald-400">{result}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={handleClose}>
            {result ? "Close" : "Cancel"}
          </Button>
          {!result && (
            <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
              Allocate seat
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
