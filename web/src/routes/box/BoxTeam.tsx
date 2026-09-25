import { useState } from "react";

import { PageHeader } from "@/components/AppShell";
import { Badge, Button, Card, EmptyState, ErrorState, Field, LoadingList, SectionTitle, Sheet, Toast } from "@/components/ui";
import { useAssignCoach, useBoxMembers, useCreateCoach } from "@/lib/boxQueries";
import { useCurrentUser } from "@/lib/auth";
import type { BoxMember } from "@/lib/types";

type ToastState = { message: string; tone: "done" | "danger" } | null;

/**
 * Equipo del box (solo el dueño): da de alta coaches y decide qué coach atiende a cada atleta.
 * Un atleta sin coach queda "del box" y recibe los mesociclos generales de los grupos donde el
 * dueño lo incluya.
 */
export default function BoxTeam() {
  const me = useCurrentUser();
  const coaches = useBoxMembers("coach");
  const athletes = useBoxMembers("athlete");
  const assign = useAssignCoach();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  // El dueño también puede atender atletas directamente (es un coach con más alcance)
  const coachOptions: { id: string; name: string }[] = [
    { id: me.id, name: `${me.full_name} (tú)` },
    ...(coaches.data ?? []).map((c) => ({ id: c.id, name: c.full_name })),
  ];
  const withoutCoach = (athletes.data ?? []).filter((a) => !a.coach_id).length;

  function handleAssign(athlete: BoxMember, coachId: string | null) {
    assign.mutate(
      { athleteId: athlete.id, coachId },
      {
        onSuccess: (res) =>
          setToast({
            message: res.coach_name
              ? `${athlete.full_name} ahora entrena con ${res.coach_name}.`
              : `${athlete.full_name} quedó como atleta del box.`,
            tone: "done",
          }),
        onError: (err) => setToast({ message: err instanceof Error ? err.message : "No se pudo asignar.", tone: "danger" }),
      },
    );
  }

  return (
    <>
      <PageHeader
        title="Coaches y atletas"
        back="/box"
        action={
          <button
            type="button"
            onClick={() => setSheetOpen(true)}
            className="min-h-10 rounded-xl bg-brand px-3 text-sm font-semibold text-on-brand active:bg-brand/85"
          >
            + Coach
          </button>
        }
      />

      <SectionTitle>Coaches</SectionTitle>
      {coaches.isPending && <LoadingList rows={2} />}
      {coaches.error && <ErrorState error={coaches.error} onRetry={() => void coaches.refetch()} />}
      {coaches.data?.length === 0 && (
        <EmptyState
          title="Todavía no tienes coaches"
          action={<Button onClick={() => setSheetOpen(true)}>Agregar coach</Button>}
        >
          Agrégalos para que programen a sus propios atletas.
        </EmptyState>
      )}
      <div className="space-y-2">
        {coaches.data?.map((coach) => {
          const count = (athletes.data ?? []).filter((a) => a.coach_id === coach.id).length;
          return (
            <Card key={coach.id} className="flex items-center justify-between gap-3 p-3">
              <div className="min-w-0">
                <p className="truncate font-semibold">{coach.full_name}</p>
                <p className="truncate text-sm text-muted">{coach.email}</p>
              </div>
              <Badge tone="brand">{count === 1 ? "1 atleta" : `${count} atletas`}</Badge>
            </Card>
          );
        })}
      </div>

      <SectionTitle
        action={withoutCoach > 0 && <span className="text-xs font-semibold text-warn">{withoutCoach} sin coach</span>}
      >
        Atletas
      </SectionTitle>
      {athletes.isPending && <LoadingList rows={3} />}
      {athletes.error && <ErrorState error={athletes.error} onRetry={() => void athletes.refetch()} />}
      {athletes.data?.length === 0 && (
        <EmptyState title="Todavía no hay atletas">
          Comparte el link de invitación de tu box para que se registren.
        </EmptyState>
      )}
      <div className="space-y-2">
        {athletes.data?.map((athlete) => (
          <Card key={athlete.id} className="p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-semibold">{athlete.full_name}</p>
                <p className="truncate text-sm text-muted">{athlete.email}</p>
              </div>
              {!athlete.coach_id && <Badge tone="warn">Del box</Badge>}
            </div>
            <label className="mt-2 block">
              <span className="sr-only">Coach de {athlete.full_name}</span>
              <select
                value={athlete.coach_id ?? ""}
                disabled={assign.isPending}
                onChange={(event) => handleAssign(athlete, event.target.value || null)}
                className="min-h-11 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-sm disabled:opacity-60"
              >
                <option value="">Sin coach — recibe los mesociclos generales</option>
                {coachOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    Coach: {c.name}
                  </option>
                ))}
              </select>
            </label>
          </Card>
        ))}
      </div>

      <CreateCoachSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        onCreated={(name) => setToast({ message: `${name} ya puede entrar como coach.`, tone: "done" })}
      />
      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={() => setToast(null)} />}
    </>
  );
}

function CreateCoachSheet({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (name: string) => void;
}) {
  const create = useCreateCoach();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    create.mutate(
      { full_name: fullName.trim(), email: email.trim(), password },
      {
        onSuccess: (coach) => {
          onCreated(coach.full_name);
          setFullName("");
          setEmail("");
          setPassword("");
          onClose();
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo crear el coach."),
      },
    );
  }

  return (
    <Sheet open={open} onClose={onClose} title="Agregar coach">
      <form onSubmit={handleSubmit} className="space-y-3 pb-4">
        <Field label="Nombre completo" required maxLength={100} value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <Field label="Correo" type="email" inputMode="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field
          label="Contraseña inicial"
          type="text"
          autoComplete="off"
          required
          minLength={8}
          hint="Compártela con tu coach para que entre por primera vez."
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <Button type="submit" full loading={create.isPending}>
          Crear cuenta de coach
        </Button>
      </form>
    </Sheet>
  );
}
