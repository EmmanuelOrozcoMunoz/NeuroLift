import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { CoverUploader } from "@/components/CoverImage";
import { CreateMesocycleSheet } from "@/components/CreateMesocycleSheet";
import { IconChevronRight, IconTrash } from "@/components/icons";
import { Badge, Button, Card, EmptyState, ErrorState, Field, LoadingList, Sheet, Toast } from "@/components/ui";
import {
  coachKeys,
  useAddGroupMembers,
  useAthletes,
  useDeleteGroup,
  useGroupDetail,
  useGroupMesocycles,
  useRemoveGroupMember,
  useSearchAthleteByEmail,
} from "@/lib/coachQueries";
import { shortDate } from "@/lib/dates";
import type { AthleteLookup } from "@/lib/types";

/** Busca por correo exacto a un atleta que todavía no es "tuyo" (se auto-registró por su
 *  cuenta), para poder agregarlo a este grupo. GET /users/athletes solo trae tus propios
 *  atletas, así que uno recién auto-registrado no aparece ahí hasta que lo agregues aquí.
 *  El backend solo devuelve atletas SIN afiliar (ver users.py:search_athlete_by_email). */
function SearchAndAddByEmail({ onFound }: { onFound: (athlete: AthleteLookup) => void }) {
  const search = useSearchAthleteByEmail();
  const [email, setEmail] = useState("");

  function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    if (!email.trim()) return;
    search.mutate(email, { onSuccess: onFound });
  }

  return (
    <form onSubmit={handleSearch} className="space-y-2 border-b border-line pb-4">
      <p className="text-xs font-semibold tracking-wide text-muted uppercase">
        Un atleta que se registró por su cuenta
      </p>
      <div className="flex items-end gap-2">
        <Field
          label="Su correo exacto"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="grow"
        />
        <Button type="submit" loading={search.isPending}>
          Buscar
        </Button>
      </div>
      {search.isError && (
        <p className="text-sm font-medium text-danger">
          {search.error instanceof Error ? search.error.message : "No se encontró ese atleta."}
        </p>
      )}
    </form>
  );
}

function AddMembersSheet({
  open,
  onClose,
  groupId,
  currentIds,
}: {
  open: boolean;
  onClose: () => void;
  groupId: string;
  currentIds: Set<string>;
}) {
  const athletes = useAthletes();
  const addMembers = useAddGroupMembers(groupId);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [found, setFound] = useState<AthleteLookup | null>(null);

  const disponibles = (athletes.data ?? []).filter((a) => !currentIds.has(a.id));

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function addOne(id: string) {
    addMembers.mutate([id], {
      onSuccess: () => {
        setFound(null);
        onClose();
      },
    });
  }

  return (
    <Sheet open={open} onClose={onClose} title="Añadir atletas">
      <div className="space-y-4">
        <SearchAndAddByEmail onFound={setFound} />

        {found &&
          (currentIds.has(found.id) ? (
            <p className="text-sm text-muted">{found.full_name} ya está en este grupo.</p>
          ) : (
            <Card className="flex items-center justify-between p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{found.full_name}</p>
                <p className="truncate text-xs text-muted">{found.email}</p>
              </div>
              <Button loading={addMembers.isPending} onClick={() => addOne(found.id)}>
                Añadir
              </Button>
            </Card>
          ))}

        {disponibles.length === 0 ? (
          <p className="text-sm text-muted">Todos tus atletas ya están en este grupo.</p>
        ) : (
          <>
            <div className="space-y-1.5">
              {disponibles.map((athlete) => (
                <label key={athlete.id} className="flex items-center gap-3 rounded-xl bg-surface-2 px-3 py-2.5">
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
            <Button
              full
              loading={addMembers.isPending}
              disabled={selected.size === 0}
              onClick={() =>
                addMembers.mutate([...selected], {
                  onSuccess: () => {
                    setSelected(new Set());
                    onClose();
                  },
                })
              }
            >
              Añadir seleccionados
            </Button>
          </>
        )}
      </div>
    </Sheet>
  );
}

export default function GroupDetail() {
  const { groupId } = useParams<{ groupId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: group, isPending, error, refetch } = useGroupDetail(groupId);
  const programs = useGroupMesocycles(groupId);
  const removeMember = useRemoveGroupMember(groupId ?? "");
  const deleteGroup = useDeleteGroup();

  const [addOpen, setAddOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  if (isPending) {
    return (
      <>
        <PageHeader title="Grupo" back="/coach/grupos" />
        <LoadingList rows={4} />
      </>
    );
  }
  if (error || !group) {
    return (
      <>
        <PageHeader title="Grupo" back="/coach/grupos" />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }

  return (
    <>
      <PageHeader title={group.name} subtitle={`${group.members.length} atleta(s)`} back="/coach/grupos" />

      <CoverUploader
        coverPath={`/groups/${groupId}/cover`}
        uploadPath={`/groups/${groupId}/cover`}
        hasImage={group.has_cover_image}
        onChanged={() => {
          void refetch();
          void queryClient.invalidateQueries({ queryKey: coachKeys.groups });
        }}
        label="Foto de portada"
      />

      <div className="mb-2 flex items-baseline justify-between">
        <p className="text-sm font-semibold tracking-wide text-muted uppercase">Miembros</p>
        <Button onClick={() => setAddOpen(true)}>+ Añadir</Button>
      </div>

      {group.members.length === 0 ? (
        <EmptyState title="Este grupo todavía no tiene atletas" />
      ) : (
        <div className="mb-5 space-y-2">
          {group.members.map((member) => (
            <Card key={member.id} className="flex items-center justify-between p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{member.full_name}</p>
                <p className="truncate text-xs text-muted">{member.email}</p>
              </div>
              <button
                type="button"
                aria-label="Quitar del grupo"
                onClick={() => removeMember.mutate(member.id)}
                disabled={removeMember.isPending}
                className="rounded-lg p-1.5 text-danger active:bg-danger/10 disabled:opacity-40"
              >
                <IconTrash className="h-4 w-4" />
              </button>
            </Card>
          ))}
        </div>
      )}

      <div className="mb-2 flex items-baseline justify-between">
        <p className="text-sm font-semibold tracking-wide text-muted uppercase">Mesociclos del grupo</p>
        <Button onClick={() => setCreateOpen(true)}>+ Crear</Button>
      </div>

      {programs.isPending && <LoadingList rows={2} />}
      {!programs.isPending && programs.error && (
        <ErrorState error={programs.error} onRetry={() => void programs.refetch()} />
      )}
      {!programs.isPending && !programs.error && (programs.data?.length ?? 0) === 0 && (
        <EmptyState title="Todavía no hay ningún mesociclo programado para este grupo" />
      )}

      <div className="space-y-3">
        {programs.data?.map((program) => {
          const activo = program.athletes.some((a) => a.is_active);
          return (
            <Link
              key={`${program.name}-${program.start_date}`}
              to={`/coach/grupos/${groupId}/programas/${encodeURIComponent(program.name)}/${program.start_date}`}
              className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 active:bg-surface-2"
            >
              <div className="min-w-0 grow">
                <div className="flex items-center gap-2">
                  <span className="truncate font-bold">{program.name}</span>
                  <Badge tone={activo ? "done" : "neutral"}>{activo ? "Activo" : "Finalizado"}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted">
                  {program.discipline} · desde {shortDate(program.start_date)} ·{" "}
                  {program.athletes.length} atleta(s)
                </p>
              </div>
              <IconChevronRight className="h-5 w-5 shrink-0 text-muted" />
            </Link>
          );
        })}
      </div>

      <Button
        variant="danger"
        full
        className="mt-6"
        onClick={() =>
          deleteGroup.mutate(groupId!, {
            onSuccess: () => navigate("/coach/grupos", { replace: true }),
          })
        }
      >
        Eliminar grupo
      </Button>

      <AddMembersSheet
        open={addOpen}
        onClose={() => setAddOpen(false)}
        groupId={groupId!}
        currentIds={new Set(group.members.map((m) => m.id))}
      />

      <CreateMesocycleSheet
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        target={{ type: "group", id: groupId! }}
        onCreated={(message) => setToast(message)}
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
