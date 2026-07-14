import { Inbox, AlertTriangle, Loader2 } from "lucide-react";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-zinc-400">
      <Loader2 className="animate-spin" size={22} />
      <p className="text-sm">{label}</p>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-red-500">
      <AlertTriangle size={22} />
      <p className="text-sm max-w-sm">{message}</p>
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center text-zinc-400">
      <Inbox size={22} />
      <p className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{title}</p>
      {description && <p className="text-xs max-w-sm">{description}</p>}
    </div>
  );
}
