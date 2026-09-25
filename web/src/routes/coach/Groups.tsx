import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { CoverThumbnail } from "@/components/CoverImage";
import { IconChevronRight } from "@/components/icons";
import { Button, EmptyState, ErrorState, Field, LoadingList, Sheet } from "@/components/ui";
import { useAthletes, useCreateGroup, useGroups } from "@/lib/coachQueries";
import { useCurrentUser } from "@/lib/auth";

function CreateGroupSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const athletes = useAthletes();
  const createGroup = useCreateGroup();
  const [name, setName] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function handleSubmit() {
    setError(null);
    if (!name.trim()) return setError("Dale un nombre al grupo.");
    createGroup.mutate(
      { name: name.trim(), athlete_ids: [...selected] },
      {
        onSuccess: () => {
          setName("");
          setSelected(new Set());
          onClose();
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo crear el grupo."),
      },
    );
  }

  return (
    <Sheet open={open} onClose={onClose} title="Nuevo grupo">
      <div className="space-y-4">
        <Field
          label="Nombre del grupo"
          placeholder="Ej. Bloque Fuerza A"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <div>
          <p className="mb-2 text-sm font-medium text-muted">
            Atletas a incluir (opcional, puedes añadir más después)
          </p>
          {athletes.isPending && <LoadingList rows={2} />}
          {!athletes.isPending && (athletes.data?.length ?? 0) === 0 && (
            <p className="text-sm text-muted">Todavía no tienes atletas registrados.</p>
          )}
          <div className="space-y-1.5">
            {athletes.data?.map((athlete) => (
              <label
                key={athlete.id}
                className="flex items-center gap-3 rounded-xl bg-surface-2 px-3 py-2.5"
              >
                <input
                  type="checkbox"
                  checked={selected.has(athlete.id)}
                  onChange={() => toggle(athlete.id)}
                  className="h-5 w-5 accent-brand"
                />
                <span className="text-sm">{athlete.full_name}</span>
              </label>
            ))}
          </div>
        </div>

        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <Button full loading={createGroup.isPending} onClick={handleSubmit}>
          Crear grupo
        </Button>
      </div>
    </Sheet>
  );
}

export default function Groups() {
  const user = useCurrentUser();
  const isAdmin = user.role === "admin";
  const { data, isPending, error, refetch } = useGroups();
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <>
      <PageHeader
        title={isAdmin ? "Todos los grupos" : "Mis grupos"}
        subtitle={
          isAdmin
            ? "Grupos de todos los coaches de la app"
            : "Programa mesociclos para varios atletas a la vez"
        }
        action={
          !isAdmin && (
            <button
              type="button"
              onClick={() => setSheetOpen(true)}
              className="min-h-10 rounded-xl bg-brand px-3 text-sm font-semibold text-on-brand active:bg-brand/85"
            >
              + Nuevo
            </button>
          )
        }
      />

      {isPending && <LoadingList rows={3} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!isPending && !error && (data?.length ?? 0) === 0 && (
        <EmptyState
          title={isAdmin ? "Todavía no hay grupos en la app" : "Todavía no tienes grupos"}
          action={
            !isAdmin && <Button onClick={() => setSheetOpen(true)}>Crear el primero</Button>
          }
        />
      )}

      <div className="space-y-3">
        {data?.map((group) => (
          <Link
            key={group.id}
            to={`/coach/grupos/${group.id}`}
            className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 active:bg-surface-2"
          >
            <CoverThumbnail coverPath={`/groups/${group.id}/cover`} hasImage={group.has_cover_image} />
            <div className="min-w-0 grow">
              <p className="truncate font-bold">{group.name}</p>
              <p className="text-sm text-muted">
                {group.member_count} atleta(s)
                {isAdmin && group.coach_name && ` · coach: ${group.coach_name}`}
              </p>
            </div>
            <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
          </Link>
        ))}
      </div>

      <CreateGroupSheet open={sheetOpen} onClose={() => setSheetOpen(false)} />
    </>
  );
}
