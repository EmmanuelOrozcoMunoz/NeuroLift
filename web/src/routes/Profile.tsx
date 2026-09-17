import { useState } from "react";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/AppShell";
import { AvatarUploader } from "@/components/AvatarUploader";
import { IconChevronRight, IconLogout } from "@/components/icons";
import { Button, Card, EmptyState, ErrorState, Field, LoadingList, Toast } from "@/components/ui";
import { WeightUnitToggle } from "@/components/WeightUnitToggle";
import { useAuth, useCurrentUser } from "@/lib/auth";
import { COMMON_PR_EXERCISES } from "@/lib/exercises";
import { formatWeight, toKg, useWeightUnit } from "@/lib/units";
import { usePersonalRecords, useUpsertPersonalRecord } from "@/lib/queries";

export default function Profile() {
  const user = useCurrentUser();
  const { logout } = useAuth();
  const { data: prs, isPending, error, refetch } = usePersonalRecords(user.id);
  const upsertPr = useUpsertPersonalRecord(user.id);
  const unit = useWeightUnit();

  const [exercise, setExercise] = useState<string>(COMMON_PR_EXERCISES[0]);
  const [weight, setWeight] = useState("");
  const [toast, setToast] = useState<string | null>(null);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const entered = Number(weight);
    if (!exercise.trim() || !(entered > 0)) return;
    const kg = toKg(entered, unit);

    upsertPr.mutate(
      { exercise_name: exercise.trim(), max_weight_kg: kg },
      {
        onSuccess: (response) => {
          setToast(response.message ?? "¡Marca guardada!");
          setExercise(COMMON_PR_EXERCISES[0]);
          setWeight("");
        },
      },
    );
  }

  return (
    <>
      <PageHeader title="Perfil" />

      <Card className="mb-4">
        <AvatarUploader />
      </Card>

      <Card className="mb-4">
        <WeightUnitToggle />
      </Card>

      <Link
        to="/perfil/fit-level"
        className="mb-4 flex items-center justify-between rounded-2xl border border-line bg-surface p-4 active:bg-surface-2"
      >
        <div>
          <p className="font-bold">🎯 Calcula tu Fit Level</p>
          <p className="text-sm text-muted">Halterofilia, gimnasia y metcon</p>
        </div>
        <IconChevronRight className="h-5 w-5 text-muted" />
      </Link>

      <h2 className="mt-6 mb-2 text-sm font-semibold tracking-wide text-muted uppercase">Mis récords (PRs)</h2>

      {isPending && <LoadingList rows={2} />}
      {!isPending && error && <ErrorState error={error} onRetry={() => void refetch()} />}

      {!isPending && !error && (prs?.length ?? 0) === 0 && (
        <EmptyState title="Todavía no tienes marcas registradas" />
      )}

      {!isPending && !error && (prs?.length ?? 0) > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {prs!.map((pr) => (
            <Card key={pr.id} className="p-3">
              <p className="truncate text-xs font-semibold text-muted">{pr.exercise_name}</p>
              <p className="mt-0.5 text-lg font-bold">{formatWeight(pr.max_weight_kg, unit)}</p>
              <p className="text-xs text-muted">{pr.last_updated.split("T")[0]}</p>
            </Card>
          ))}
        </div>
      )}

      <Card className="mt-4">
        <p className="mb-3 font-bold">Registrar nueva marca</p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-muted">Ejercicio</span>
            <select
              value={exercise}
              onChange={(event) => setExercise(event.target.value)}
              className="min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg"
            >
              {COMMON_PR_EXERCISES.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <Field
            label={`1RM en ${unit}`}
            type="number"
            inputMode="decimal"
            step={unit === "lb" ? "5" : "2.5"}
            min="0"
            value={weight}
            onChange={(event) => setWeight(event.target.value)}
            required
          />
          <Button type="submit" full loading={upsertPr.isPending}>
            Guardar marca
          </Button>
        </form>
      </Card>

      <Button variant="danger" full className="mt-6" onClick={() => void logout()}>
        <IconLogout className="h-5 w-5" />
        Cerrar sesión
      </Button>

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}
