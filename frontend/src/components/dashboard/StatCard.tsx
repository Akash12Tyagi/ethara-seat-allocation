import { Card } from "@/components/ui/Card";
import type { LucideIcon } from "lucide-react";
import { clsx } from "clsx";

export function StatCard({
  label,
  value,
  icon: Icon,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
  tone?: "neutral" | "emerald" | "amber" | "blue" | "zinc";
}) {
  const toneClasses: Record<string, string> = {
    neutral: "bg-zinc-100 text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400",
    emerald: "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400",
    amber: "bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400",
    blue: "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400",
    zinc: "bg-zinc-100 text-zinc-500 dark:bg-zinc-900 dark:text-zinc-500",
  };

  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <div className={clsx("flex h-9 w-9 items-center justify-center rounded-lg", toneClasses[tone])}>
          <Icon size={18} />
        </div>
        <div>
          <p className="text-xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{value}</p>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
        </div>
      </div>
    </Card>
  );
}
