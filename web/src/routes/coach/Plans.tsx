import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { AssignPlanSheet } from "@/components/AssignPlanSheet";
import { CoverThumbnail } from "@/components/CoverImage";
import { WeekdayPicker } from "@/components/WeekdayPicker";
import { Badge, Button, Card, EmptyState, ErrorState, Field, LoadingList, Segmented, Sheet, Toast } from "@/components/ui";
import { useCreatePlan, useDeletePlan, useGeneratePlanWithAI, useMyPlans, usePublishPlan } from "@/lib/coachQueries";
import { formatPrice } from "@/lib/dates";
import type { PlanLevel, PlanSummary, PlanVisibility, Weekday } from "@/lib/types";

const DISCIPLINAS = ["Powerbuilding", "Powerlifting", "Hipertrofia", "Weightlifting", "CrossFit"];
const NIVELES: PlanLevel[] = ["Principiante", "Intermedio", "Avanzado"];

type ModoCreacion = "manual" | "ia";

function CreatePlanSheet({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (message: string) => void }) {
  const createPlan = useCreatePlan();
  const generateAI = useGeneratePlanWithAI();
  const [modo, setModo] = useState<ModoCreacion>("manual");
  const [context, setContext] = useState("");
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

    if (modo === "ia") {
      generateAI.mutate(
        {
          name: name.trim(),
          description: description.trim(),
          discipline,
          level,
          weeks_count: Math.min(weeks, 16),
          training_days: days,
          context: context.trim(),
          session_duration_minutes: null,
        },
        {
          onSuccess: () => {
            setName("");
            setDescription("");
            setContext("");
            onCreated("¡Plantilla generada! Revísala y edítala, luego asígnala a un grupo.");
            onClose();
          },
          onError: (err) => setError(err instanceof Error ? err.message : "No se pudo generar la plantilla."),
        },
      );
      return;
    }

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
          onCreated("¡Plan creado! Ahora agrégale ejercicios.");
          onClose();
        },
        onError: (err) => setError(err instanceof Error ? err.message : "No se pudo crear el plan."),
      },
    );
  }

  return (
    <Sheet open={open} onClose={onClose} title="Nuevo plan">
      <div className="space-y-4">
        <Segmented<ModoCreacion>
          value={modo}
          onChange={setModo}
          options={[
            { value: "manual", label: "Armarlo yo" },
            { value: "ia", label: "✨ Con IA" },
          ]}
        />
        {modo === "ia" && (
          <p className="text-xs text-muted">
            La IA arma la plantilla una sola vez, con las cargas en % de 1RM. Al asignarla a un grupo, cada
            atleta recibe sus propios kg según sus marcas. Puede tardar un minuto.
          </p>
        )}

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

        {modo === "manual" ? (
          <Field
            label="Precio (vacío = gratis)"
            type="number"
            inputMode="decimal"
            min="0"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        ) : (
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-muted">¿Qué quieres que trabaje? (opcional)</span>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="Ej. CrossFit intermedio, 5 días, énfasis en levantamientos olímpicos y un WOD corto cada día"
              className="w-full rounded-xl border border-line bg-surface-2 px-3.5 py-2.5 text-fg placeholder:text-muted/50 focus:border-brand focus:outline-none"
            />
          </label>
        )}

        <Field
          label="Semanas de duración"
          type="number"
          min="1"
          max={modo === "ia" ? 16 : 52}
          value={weeks}
          onChange={(e) => setWeeks(Number(e.target.value) || 1)}
        />

        <div>
          <span className="mb-1.5 block text-sm font-medium text-muted">Días de entrenamiento por semana</span>
          <WeekdayPicker value={days} onChange={setDays} />
        </div>

        {error && <p className="text-sm font-medium text-danger">{error}</p>}
        <Button full loading={createPlan.isPending || generateAI.isPending} onClick={handleSubmit}>
          {modo === "ia" ? "Generar plantilla" : "Crear plan"}
        </Button>
      </div>
    </Sheet>
  );
}

const VISIBILITY_OPTIONS: { value: PlanVisibility; title: string; description: string }[] = [
  { value: "box", title: "Solo mi box", description: "Lo ven y adquieren únicamente los atletas de tu box." },
  {
    value: "public",
    title: "Toda la plataforma",
    description: "Cualquier atleta de NeuroLift, de cualquier box, lo verá en el catálogo.",
  },
];

/** Al publicar, el coach decide quién puede ver el plan en el catálogo. */
function PublishSheet({
  plan,
  onClose,
  onDone,
}: {
  plan: PlanSummary | null;
  onClose: () => void;
  onDone: (message: string) => void;
}) {
  const publish = usePublishPlan();
  const [visibility, setVisibility] = useState<PlanVisibility>("box");

  return (
    <Sheet open={plan !== null} onClose={onClose} title="¿Quién puede verlo?">
      <div className="space-y-2 pb-4">
        {VISIBILITY_OPTIONS.map((option) => (
          <label
            key={option.value}
            className={`flex cursor-pointer gap-3 rounded-xl border p-3 ${
              visibility === option.value ? "border-brand bg-brand-soft" : "border-line bg-surface-2"
            }`}
          >
            <input
              type="radio"
              name="visibility"
              className="mt-1 accent-[var(--color-brand)]"
              checked={visibility === option.value}
              onChange={() => setVisibility(option.value)}
            />
            <span>
              <span className="block font-semibold">{option.title}</span>
              <span className="block text-sm text-muted">{option.description}</span>
            </span>
          </label>
        ))}
        <Button
          full
          className="mt-2"
          loading={publish.isPending}
          onClick={() =>
            plan &&
            publish.mutate(
              { planId: plan.id, isPublished: true, visibility },
              {
                onSuccess: () => {
                  onDone(visibility === "public" ? "¡Publicado para toda la plataforma!" : "¡Publicado para tu box!");
                  onClose();
                },
                onError: (err) => onDone(err instanceof Error ? err.message : "No se pudo publicar."),
              },
            )
          }
        >
          Publicar
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
  const [publishing, setPublishing] = useState<PlanSummary | null>(null);
  const [asignando, setAsignando] = useState<PlanSummary | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        title="Mis planes"
        subtitle="Tus plantillas: asígnalas a tus grupos o publícalas en el catálogo"
        action={
          <button
            type="button"
            onClick={() => setSheetOpen(true)}
            className="min-h-10 rounded-xl bg-brand px-3 text-sm font-semibold text-on-brand active:bg-brand/85"
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
                    {plan.is_published && (
                      <Badge tone="brand">{plan.visibility === "public" ? "Toda la plataforma" : "Solo mi box"}</Badge>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-muted">
                    {plan.discipline} · {plan.level} · {plan.weeks_count} sem ({plan.sessions_per_week}/sem) ·{" "}
                    {formatPrice(plan.price)}
                  </p>
                </div>
              </Link>
            </div>

            {/* Dos filas: en 375px los tres botones en una sola no cabían ("Eliminar" se salía
                de la tarjeta y "Editar contenido" se partía en dos líneas) */}
            <Link to={`/coach/planes/${plan.id}`} className="mt-3 block">
              <Button variant="secondary" full>
                Editar contenido
              </Button>
            </Link>
            <Button className="mt-2" full onClick={() => setAsignando(plan)}>
              Asignar a un grupo
            </Button>
            <div className="mt-2 flex gap-2">
              <Button
                variant="secondary"
                className="flex-1"
                loading={publish.isPending}
                onClick={() =>
                  plan.is_published
                    ? publish.mutate(
                        { planId: plan.id, isPublished: false },
                        {
                          onSuccess: () => setToast("Plan despublicado."),
                          onError: (err) => setToast(err instanceof Error ? err.message : "No se pudo actualizar."),
                        },
                      )
                    : setPublishing(plan)
                }
              >
                {plan.is_published ? "Despublicar" : "Publicar"}
              </Button>
              <Button
                variant="danger"
                className="flex-1"
                onClick={() => deletePlan.mutate(plan.id, { onSuccess: () => setToast("Plan eliminado.") })}
              >
                Eliminar
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <AssignPlanSheet
        open={asignando !== null}
        onClose={() => setAsignando(null)}
        plan={asignando ? { id: asignando.id, name: asignando.name } : undefined}
      />
      <PublishSheet plan={publishing} onClose={() => setPublishing(null)} onDone={setToast} />
      <CreatePlanSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        onCreated={setToast}
      />

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
