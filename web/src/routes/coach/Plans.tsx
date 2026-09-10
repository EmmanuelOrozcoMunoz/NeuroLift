import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { CoverThumbnail } from "@/components/CoverImage";
import { WeekdayPicker } from "@/components/WeekdayPicker";
import { Badge, Button, Card, EmptyState, ErrorState, Field, LoadingList, Sheet, Toast } from "@/components/ui";
import { useCreatePlan, useDeletePlan, useMyPlans, usePublishPlan } from "@/lib/coachQueries";
import { formatPrice } from "@/lib/dates";
import type { PlanLevel, Weekday } from "@/lib/types";

const DISCIPLINAS = ["Powerbuilding", "Powerlifting", "Hipertrofia", "Weightlifting", "CrossFit"];
const NIVELES: PlanLevel[] = ["Principiante", "Intermedio", "Avanzado"];

function CreatePlanSheet({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const createPlan = useCreatePlan();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [discipline, setDiscipline] = useState(DISCIPLINAS[0]);
  const [level, setLevel] = useState<PlanLevel>("Intermedio");
  const [price, setPrice] = useState("");
  const [weeks, setWeeks] = useState(8);
  const [days, setDays] = useState<Weekday[]>([0, 2, 4]);
  const [error, setError] = useState<string | null>(null);

  function handleSubmit() {
    setError(null);
    if (!name.trim()) return setError("Dale un nombre al plan.");
    if (days.length === 0) return setError("Selecciona al menos un día de entrenamiento.");
    const precioNum = Number(price);

    createPlan.mutate(
      {
        name: name.trim(),
        description: description.trim(),
        discipline,
        level,
        price: price && precioNum > 0 ? precioNum : null,
        weeks_count: weeks,
        training_days: days,
      },
      {
        onSuccess: () => {
          setName("");
          setDescription("");
          setPrice("");
          onCreated();
          onClose();
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo crear el plan."),
      },
    );
  }

  return (
    <Sheet open={open} onClose={onClose} title="Nuevo plan">
      <div className="space-y-4">
        <Field
          label="Nombre del plan"
          placeholder="Ej. Fuerza Base — 8 semanas"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Descripción (para el catálogo)</span>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            maxLength={2000}
            placeholder="Para quién es, qué resultados busca, qué equipo necesita..."
            className="w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-fg placeholder:text-muted/50 focus:border-brand focus:outline-none"
          />
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Disciplina</span>
          <select
            value={discipline}
            onChange={(e) => setDiscipline(e.target.value)}
            className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
          >
            {DISCIPLINAS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-muted">Nivel</span>
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value as PlanLevel)}
            className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
          >
            {NIVELES.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <Field
          label="Precio (vacío = gratis)"
          type="number"
          inputMode="decimal"
          min="0"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
        />

        <Field
          label="Semanas de duración"
          type="number"
          min="1"
          max="52"
          value={weeks}
          onChange={(e) => setWeeks(Number(e.target.value) || 1)}
        />

        <div>
          <span className="mb-1.5 block text-sm font-medium text-muted">Días de entrenamiento por semana</span>
          <WeekdayPicker value={days} onChange={setDays} />
        </div>

        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <Button full loading={createPlan.isPending} onClick={handleSubmit}>
          Crear plan
        </Button>
      </div>
    </Sheet>
  );
}

export default function Plans() {
  const { data, isPending, error, refetch } = useMyPlans();
  const publish = usePublishPlan();
  const deletePlan = useDeletePlan();
  const [sheetOpen, setSheetOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        title="Mis planes"
        subtitle="Plantillas que cualquier atleta puede adquirir por su cuenta"
        action={
          <button
            type="button"
            onClick={() => setSheetOpen(true)}
            className="min-h-10 rounded-xl bg-brand px-3 text-sm font-semibold text-white active:bg-brand/85"
          >
            + Nuevo
          </button>
        }
      />

      {isPending && <LoadingList rows={3} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!isPending && !error && (data?.length ?? 0) === 0 && (
        <EmptyState
          title="Todavía no has creado ningún plan"
          action={<Button onClick={() => setSheetOpen(true)}>Crear el primero</Button>}
        />
      )}

      <div className="space-y-3">
        {data?.map((plan) => (
          <Card key={plan.id}>
            <div className="flex items-start justify-between gap-2">
              <Link to={`/coach/planes/${plan.id}`} className="flex min-w-0 grow items-center gap-3">
                <CoverThumbnail coverPath={`/plans/${plan.id}/cover`} hasImage={plan.has_cover_image} />
                <div className="min-w-0 grow">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold">{plan.name}</span>
                    <Badge tone={plan.is_published ? "done" : "neutral"}>
                      {plan.is_published ? "Publicado" : "Borrador"}
                    </Badge>
                  </div>
                  <p className="mt-1 text-sm text-muted">
                    {plan.discipline} · {plan.level} · {plan.weeks_count} sem ({plan.sessions_per_week}/sem) ·{" "}
                    {formatPrice(plan.price)}
                  </p>
                </div>
              </Link>
            </div>

            <div className="mt-3 flex gap-2">
              <Link to={`/coach/planes/${plan.id}`} className="grow">
                <Button variant="secondary" full>
                  Editar contenido
                </Button>
              </Link>
              <Button
                variant={plan.is_published ? "secondary" : "primary"}
                loading={publish.isPending}
                onClick={() =>
                  publish.mutate(
                    { planId: plan.id, isPublished: !plan.is_published },
                    {
                      onSuccess: () => setToast(plan.is_published ? "Plan despublicado." : "¡Plan publicado!"),
                      onError: (err) => setToast(err instanceof Error ? err.message : "No se pudo actualizar."),
                    },
                  )
                }
              >
                {plan.is_published ? "Despublicar" : "Publicar"}
              </Button>
              <Button
                variant="danger"
                onClick={() => deletePlan.mutate(plan.id, { onSuccess: () => setToast("Plan eliminado.") })}
              >
                Eliminar
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <CreatePlanSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        onCreated={() => setToast("¡Plan creado! Ahora agrégale ejercicios.")}
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
