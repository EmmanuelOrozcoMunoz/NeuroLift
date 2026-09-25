import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { Card, ErrorState, LoadingList, SectionTitle } from "@/components/ui";
import { useAdminOverview } from "@/lib/adminQueries";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <Card className="text-center">
      <p className="text-2xl font-bold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </Card>
  );
}

export default function AdminOverview() {
  const { data, isPending, error, refetch } = useAdminOverview();

  return (
    <>
      <PageHeader title="Panel de Administración" subtitle="Visibilidad total sobre la app" />

      {isPending && <LoadingList rows={3} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {data && (
        <>
          <SectionTitle
            action={
              data.boxes_pending > 0 && (
                <Link to="/admin/boxes" className="text-xs font-semibold text-warn">
                  {data.boxes_pending} por aprobar
                </Link>
              )
            }
          >
            Boxes
          </SectionTitle>
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Boxes activos" value={data.total_boxes} />
            <Stat label="Solicitudes pendientes" value={data.boxes_pending} />
          </div>

          <SectionTitle>Usuarios</SectionTitle>
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Usuarios totales" value={data.total_users} />
            <Stat label="Coaches" value={data.total_coaches} />
            <Stat label="Atletas" value={data.total_athletes} />
            <Stat label="Admins" value={data.total_admins} />
          </div>

          <SectionTitle>Entrenamiento</SectionTitle>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Grupos" value={data.total_groups} />
            <Stat label="Mesociclos" value={data.total_mesocycles} />
            <Stat label="Sesiones totales" value={data.total_sessions} />
          </div>

          <div className="mt-3 grid grid-cols-2 gap-3">
            <Stat label="Sesiones completadas" value={data.sessions_completed} />
            <Stat label="Sesiones pendientes" value={data.sessions_pending} />
          </div>
        </>
      )}
    </>
  );
}
