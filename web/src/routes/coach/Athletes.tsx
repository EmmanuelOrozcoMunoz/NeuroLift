import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { AtletasTabs } from "@/components/AtletasTabs";
import { IconChevronRight, IconUser } from "@/components/icons";
import { Badge, Button, EmptyState, ErrorState, Field, LoadingList, Sheet, Toast } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import { useAthleteLeaderboard, useAthletes, useRegisterAthlete } from "@/lib/coachQueries";
import { RankingDelBox } from "@/routes/Ranking";

function RegisterAthleteSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const register = useRegisterAthlete();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [bodyWeight, setBodyWeight] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function reset() {
    setFullName("");
    setEmail("");
    setPassword("");
    setBodyWeight("");
    setError(null);
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) return setError("La contraseña debe tener al menos 8 caracteres.");

    const peso = Number(bodyWeight);
    register.mutate(
      {
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        role: "athlete",
        body_weight: bodyWeight && peso > 0 ? peso : null,
      },
      {
        onSuccess: (response) => {
          // Mensaje genérico del backend a propósito: no revela si el correo ya estaba
          // registrado (evita usar este formulario para enumerar cuentas existentes).
          setMessage(response.message ?? "Solicitud procesada.");
          reset();
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo registrar al atleta."),
      },
    );
  }

  return (
    <Sheet
      open={open}
      onClose={() => {
        setMessage(null);
        onClose();
      }}
      title="Nuevo atleta"
    >
      <p className="mb-4 text-sm text-muted">
        Se crea una cuenta con una contraseña temporal; compártesela al atleta para que inicie
        sesión.
      </p>

      {message ? (
        <div className="space-y-4">
          <p className="rounded-xl bg-done-soft px-4 py-3 text-sm font-medium text-done">{message}</p>
          <Button
            full
            onClick={() => {
              setMessage(null);
              onClose();
            }}
          >
            Listo
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Nombre completo" required value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <Field
            label="Correo electrónico"
            type="email"
            inputMode="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Field
            label="Contraseña temporal"
            type="password"
            required
            minLength={8}
            hint="Mínimo 8 caracteres. El atleta podrá cambiarla después."
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Field
            label="Peso corporal (kg)"
            type="number"
            inputMode="decimal"
            step="0.5"
            min="0"
            hint="Opcional."
            value={bodyWeight}
            onChange={(e) => setBodyWeight(e.target.value)}
          />
          {error && <p className="text-sm font-medium text-danger">{error}</p>}
          <Button type="submit" full loading={register.isPending}>
            Registrar atleta
          </Button>
        </form>
      )}
    </Sheet>
  );
}

export default function Athletes() {
  const { data, isPending, error, refetch } = useAthletes();
  // La actividad de cada atleta (cuántos entrenos completó esta semana y su último WOD) va en su propia fila: ya
  // no hay una pantalla aparte de "Actividad"
  const actividad = useAthleteLeaderboard();
  const [params] = useSearchParams();
  const verRanking = params.get("vista") === "ranking";
  const actividadDe = new Map((actividad.data ?? []).map((a) => [a.user_id, a]));
  const me = useCurrentUser();
  const isOwner = me.role === "owner" && me.box?.kind === "box";
  const [sheetOpen, setSheetOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        title={isOwner ? "Atletas del box" : "Atletas"}
        subtitle={isOwner ? "Todos, con y sin coach" : undefined}
        action={
          <button
            type="button"
            onClick={() => setSheetOpen(true)}
            className="min-h-11 rounded-xl bg-brand px-3 text-sm font-semibold text-on-brand active:bg-brand/85"
          >
            + Nuevo
          </button>
        }
      />

      <div className="mb-3">
        <AtletasTabs activa={verRanking ? "ranking" : "atletas"} />
      </div>

      {verRanking && <RankingDelBox esAtleta={false} />}

      {!verRanking && isPending && <LoadingList rows={4} />}
      {!verRanking && !isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!verRanking && !isPending && !error && (data?.length ?? 0) === 0 && (
        <EmptyState
          icon={<IconUser className="h-10 w-10" />}
          title="Todavía no tienes atletas"
          action={<Button onClick={() => setSheetOpen(true)}>Registrar el primero</Button>}
        />
      )}

      <div className="space-y-3">
        {!verRanking && data?.map((athlete) => (
          <Link
            key={athlete.id}
            to={`/coach/atletas/${athlete.id}`}
            className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 active:bg-surface-2"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-soft text-brand">
              <IconUser className="h-5 w-5" />
            </div>
            <div className="min-w-0 grow">
              <p className="truncate font-bold">{athlete.full_name}</p>
              <p className="truncate text-sm text-muted">{athlete.email}</p>
              {actividadDe.get(athlete.id)?.last_wod_summary && (
                <p className="truncate text-xs font-semibold text-brand">{actividadDe.get(athlete.id)?.last_wod_summary}</p>
              )}
            </div>
            {actividadDe.get(athlete.id) && (
              <div className="shrink-0 whitespace-nowrap">
                <Badge tone={(actividadDe.get(athlete.id)?.completed_this_week ?? 0) > 0 ? "done" : "neutral"}>
                  {actividadDe.get(athlete.id)?.completed_this_week ?? 0} esta semana
                </Badge>
              </div>
            )}
            <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
          </Link>
        ))}
      </div>

      <RegisterAthleteSheet
        open={sheetOpen}
        onClose={() => {
          setSheetOpen(false);
          setToast("Atleta procesado.");
        }}
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
