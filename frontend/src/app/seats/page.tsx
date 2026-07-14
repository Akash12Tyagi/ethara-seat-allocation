"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { seatsApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select, Label } from "@/components/ui/Input";
import { Badge, type BadgeVariant } from "@/components/ui/Badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/States";
import { Modal } from "@/components/ui/Modal";
import { Plus, ArmchairIcon } from "lucide-react";

const PAGE_SIZE = 30;

export default function SeatsPage() {
  const queryClient = useQueryClient();
  const [floor, setFloor] = useState("");
  const [zone, setZone] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);

  const params = useMemo(
    () => ({
      floor: floor ? Number(floor) : undefined,
      zone: zone || undefined,
      status: status || undefined,
      page,
      page_size: PAGE_SIZE,
    }),
    [floor, zone, status, page]
  );

  const seats = useQuery({ queryKey: ["seats", params], queryFn: () => seatsApi.list(params) });

  const releaseMutation = useMutation({
    mutationFn: (seatId: number) => seatsApi.release({ seat_id: seatId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["seats"] });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  function resetAnd(fn: () => void) {
    fn();
    setPage(1);
  }

  return (
    <>
      <PageHeader
        title="Seats"
        description={seats.data ? `${seats.data.total.toLocaleString()} total` : undefined}
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus size={15} /> Add Seat
          </Button>
        }
      />

      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        <Card className="p-3">
          <div className="flex flex-wrap gap-3">
            <Input
              placeholder="Floor"
              type="number"
              className="w-28"
              value={floor}
              onChange={(e) => resetAnd(() => setFloor(e.target.value))}
            />
            <Input
              placeholder="Zone (e.g. A)"
              className="w-32"
              value={zone}
              onChange={(e) => resetAnd(() => setZone(e.target.value.toUpperCase()))}
            />
            <Select className="w-auto min-w-[160px]" value={status} onChange={(e) => resetAnd(() => setStatus(e.target.value))}>
              <option value="">Any status</option>
              <option value="available">Available</option>
              <option value="occupied">Occupied</option>
              <option value="reserved">Reserved</option>
              <option value="maintenance">Maintenance</option>
            </Select>
          </div>
        </Card>

        <Card>
          {seats.isLoading && <LoadingState label="Loading seats..." />}
          {seats.isError && <ErrorState message="Could not load seats." />}
          {seats.data && seats.data.items.length === 0 && (
            <EmptyState title="No seats match these filters" />
          )}

          {seats.data && seats.data.items.length > 0 && (
            <>
              <div className="grid grid-cols-2 gap-2 p-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
                {seats.data.items.map((s) => (
                  <div
                    key={s.id}
                    className="rounded-lg border border-zinc-200 p-3 text-xs dark:border-zinc-800"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-semibold text-zinc-800 dark:text-zinc-100">{s.code}</span>
                      <Badge variant={s.status as BadgeVariant}>{s.status}</Badge>
                    </div>
                    <p className="mt-1 text-zinc-400">Floor {s.floor}</p>
                    {s.allocated_employee_name ? (
                      <div className="mt-2 border-t border-zinc-100 pt-2 dark:border-zinc-800">
                        <p className="truncate font-medium text-zinc-700 dark:text-zinc-200">
                          {s.allocated_employee_name}
                        </p>
                        <p className="truncate text-zinc-400">{s.allocated_project_name}</p>
                        <button
                          onClick={() => releaseMutation.mutate(s.id)}
                          className="mt-1.5 text-[11px] font-medium text-amber-600 hover:underline"
                        >
                          Release seat
                        </button>
                      </div>
                    ) : (
                      <div className="mt-2 flex items-center gap-1.5 border-t border-zinc-100 pt-2 text-zinc-300 dark:border-zinc-800 dark:text-zinc-600">
                        <ArmchairIcon size={13} />
                        <span>Unoccupied</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between border-t border-zinc-100 px-4 py-3 dark:border-zinc-800">
                <p className="text-xs text-zinc-400">
                  Page {seats.data.page} of {seats.data.total_pages} · {seats.data.total.toLocaleString()} seats
                </p>
                <div className="flex gap-2">
                  <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
                    Previous
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={page >= seats.data.total_pages}
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

      <CreateSeatModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </>
  );
}

function CreateSeatModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [floor, setFloor] = useState("1");
  const [zone, setZone] = useState("A");
  const [bay, setBay] = useState("1");
  const [seatNumber, setSeatNumber] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      seatsApi.create({ floor: Number(floor), zone, bay, seat_number: seatNumber }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["seats"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setSeatNumber("");
      onClose();
    },
    onError: (err: unknown) => {
      setError(err instanceof Error ? err.message : "Failed to create seat");
    },
  });

  return (
    <Modal open={open} onClose={onClose} title="Add Seat">
      <div className="space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div>
            <Label>Floor</Label>
            <Input type="number" min={1} value={floor} onChange={(e) => setFloor(e.target.value)} />
          </div>
          <div>
            <Label>Zone</Label>
            <Input value={zone} onChange={(e) => setZone(e.target.value.toUpperCase())} maxLength={2} />
          </div>
          <div>
            <Label>Bay</Label>
            <Input value={bay} onChange={(e) => setBay(e.target.value)} />
          </div>
        </div>
        <div>
          <Label>Seat number</Label>
          <Input value={seatNumber} onChange={(e) => setSeatNumber(e.target.value)} placeholder="e.g. 23" />
        </div>
        {error && <p className="text-xs text-red-500">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => {
              setError(null);
              mutation.mutate();
            }}
            disabled={!seatNumber || mutation.isPending}
          >
            Create seat
          </Button>
        </div>
      </div>
    </Modal>
  );
}
