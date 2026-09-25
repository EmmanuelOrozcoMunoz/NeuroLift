import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { IconLogout } from "@/components/icons";
import { Card, ErrorState, LoadingList, SectionTitle } from "@/components/ui";
import { useAdminOverview } from "@/lib/adminQueries";
import { useAuth } from "@/lib/auth";

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
  const { logout } = useAuth();

  return (
    <>
      {/* El admin no tiene pantalla de Perfil (su barra ya usa las 5 pestañas), así que cerrar
          sesión vive aquí, en su pantalla de inicio. */}
      <PageHeader
        title="Panel de Administración"
        subtitle="Visibilidad total sobre la app"
        action={
          <button
            type="button"
            onClick={() => void logout()}
            className="flex min-h-10 items-center gap-1.5 rounded-xl border border-line px-3 text-sm font-semibold text-danger active:bg-danger/10"
          >
            <IconLogout className="h-4 w-4" />
            Salir
          </button>
        }
      />

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
