import { PageHeader } from "@/components/AppShell";
import { Badge, Card, EmptyState, ErrorState, LoadingList } from "@/components/ui";
import { useAuditLogs } from "@/lib/adminQueries";
import type { AuditLog } from "@/lib/types";

function levelTone(level: string): "neutral" | "warn" | "done" {
  if (level === "WARNING" || level === "ERROR") return "warn";
  return "neutral";
}

function formatTimestamp(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("es-CO", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function LogRow({ log }: { log: AuditLog }) {
  return (
    <Card className="space-y-1.5">
      <div className="flex items-center justify-between gap-3">
        <Badge tone={levelTone(log.level)}>{log.level}</Badge>
        <span className="text-xs text-muted">{formatTimestamp(log.created_at)}</span>
      </div>
      <p className="text-sm">{log.message}</p>
    </Card>
  );
}

export default function AdminLogs() {
  const { data, isPending, error, refetch } = useAuditLogs();

  return (
    <>
      <PageHeader title="Logs de seguridad" subtitle="Logins fallidos, cambios de rol y revocaciones" />

      {isPending && <LoadingList rows={5} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!isPending && !error && (data?.length ?? 0) === 0 && (
        <EmptyState title="Todavía no hay eventos registrados" />
      )}

      <div className="space-y-2.5">
        {data?.map((log) => <LogRow key={log.id} log={log} />)}
      </div>
    </>
  );
}
