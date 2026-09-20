import { useEffect, useState } from "react";

import { PageHeader } from "@/components/AppShell";
import { FitLevelCriteria } from "@/components/FitLevelCriteria";
import { Button, Card, ErrorState, Field, LoadingList, Segmented, Sheet, Stepper, Toast } from "@/components/ui";
import { useAuth, useCurrentUser } from "@/lib/auth";
import { useFitnessLevel, useSaveBenchmarks } from "@/lib/queries";
import { kgTo, toKg, useWeightUnit, WeightStepper } from "@/lib/units";
import type { FitCategory, WodCategory } from "@/lib/types";

const CAT_LABEL: Record<FitCategory, string> = {
  halterofilia: "🏋️ Halterofilia",
  gimnasia: "🤸 Gimnasia",
  metcon: "🔥 Metcon",
};

interface TimeValue {
  min: number;
  sec: number;
}

function secondsToTime(total: number | undefined): TimeValue {
  const t = total ?? 0;
  return { min: Math.floor(t / 60), sec: t % 60 };
}

function timeToSeconds(t: TimeValue): number {
  return t.min * 60 + t.sec;
}

export default function FitLevel() {
  const user = useCurrentUser();
  const { refreshUser } = useAuth();
  const { data, isPending, error, refetch } = useFitnessLevel(user.id);
  const save = useSaveBenchmarks(user.id);
  const unit = useWeightUnit();

  const [toast, setToast] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const [bodyWeight, setBodyWeight] = useState(0);
  const [sex, setSex] = useState<"male" | "female" | "">("");
  const [age, setAge] = useState(0);
  const [category, setCategory] = useState<WodCategory | "">("");

  const [snatch, setSnatch] = useState(0);
  const [cleanJerk, setCleanJerk] = useState(0);
  const [backSquat, setBackSquat] = useState(0);
  const [deadlift, setDeadlift] = useState(0);

  const [pullUps, setPullUps] = useState(0);
  const [pushUps, setPushUps] = useState(0);
  const [muscleUps, setMuscleUps] = useState(0);
  const [hspu, setHspu] = useState(0);

  const [fran, setFran] = useState<TimeValue>({ min: 0, sec: 0 });
  const [grace, setGrace] = useState<TimeValue>({ min: 0, sec: 0 });
  const [row2k, setRow2k] = useState<TimeValue>({ min: 0, sec: 0 });
  const [cindy, setCindy] = useState(0);

  // Sembramos el formulario con lo que ya está guardado, cada vez que llegan datos nuevos
  useEffect(() => {
    if (!data) return;
    setBodyWeight(data.body_weight ?? 0);
    setSex(data.sex ?? "");
    setAge(data.age ?? 0);
    setCategory(data.category ?? "");
    setSnatch(data.values.snatch_kg ?? 0);
    setCleanJerk(data.values.clean_jerk_kg ?? 0);
    setBackSquat(data.values.back_squat_kg ?? 0);
    setDeadlift(data.values.deadlift_kg ?? 0);
    setPullUps(data.values.pull_ups_max ?? 0);
    setPushUps(data.values.push_ups_max ?? 0);
    setMuscleUps(data.values.muscle_ups_max ?? 0);
    setHspu(data.values.hspu_max ?? 0);
    setFran(secondsToTime(data.values.fran_seconds));
    setGrace(secondsToTime(data.values.grace_seconds));
    setRow2k(secondsToTime(data.values.row_2k_seconds));
    setCindy(data.values.cindy_total_reps ?? 0);
  }, [data]);

  if (isPending) {
    return (
      <>
        <PageHeader title="Fit Level" back="/perfil" />
        <LoadingList rows={3} />
      </>
    );
  }

  if (error) {
    return (
      <>
        <PageHeader title="Fit Level" back="/perfil" />
        <ErrorState error={error} onRetry={() => void refetch()} />
      </>
    );
  }

  function handleSave() {
    const payload: Record<string, number | string> = {};
    if (bodyWeight > 0) payload.body_weight = bodyWeight;
    if (sex) payload.sex = sex;
    if (age > 0) payload.age = age;
    if (category) payload.category = category;
    if (snatch > 0) payload.snatch_kg = snatch;
    if (cleanJerk > 0) payload.clean_jerk_kg = cleanJerk;
    if (backSquat > 0) payload.back_squat_kg = backSquat;
    if (deadlift > 0) payload.deadlift_kg = deadlift;
    if (pullUps > 0) payload.pull_ups_max = pullUps;
    if (pushUps > 0) payload.push_ups_max = pushUps;
    if (muscleUps > 0) payload.muscle_ups_max = muscleUps;
    if (hspu > 0) payload.hspu_max = hspu;
    const franSec = timeToSeconds(fran);
    const graceSec = timeToSeconds(grace);
    const rowSec = timeToSeconds(row2k);
    if (franSec > 0) payload.fran_seconds = franSec;
    if (graceSec > 0) payload.grace_seconds = graceSec;
    if (rowSec > 0) payload.row_2k_seconds = rowSec;
    if (cindy > 0) payload.cindy_total_reps = cindy;

    save.mutate(payload, {
      onSuccess: () => {
        setEditing(false);
        setToast("¡Marcas guardadas! Tu Fit Level se actualizó.");
        // El sexo puede haber cambiado y afecta cosas fuera de esta pantalla (ej. la calculadora
        // de discos usa una barra distinta para hombre/mujer) — refresca el usuario actual para
        // que se vea correcto sin tener que cerrar sesión y volver a entrar.
        if (payload.sex) void refreshUser();
      },
    });
  }

  const faltaPerfil = !data?.sex || !data?.age;

  return (
    <>
      <PageHeader title="Fit Level" subtitle="Halterofilia · Gimnasia · Metcon" back="/perfil" />

      <p className="mb-4 text-sm text-muted">
        Estándares aproximados que sí diferencian por sexo y edad — úsalos como referencia, no
        como medición competitiva. Llena solo las marcas que ya tengas.
      </p>

      <FitLevelCriteria />

      {faltaPerfil && (
        <Card className="mb-4 border-warn/30 bg-warn/10">
          <p className="text-sm text-warn">
            Todavía no registraste tu sexo y/o edad — el cálculo usa un promedio neutro mientras
            tanto. Complétalos abajo para un resultado más preciso.
          </p>
        </Card>
      )}

      {data?.overall_level ? (
        <Card className="mb-4">
          {(data.sex || data.age) && (
            <p className="mb-1 text-xs text-muted">
              {[data.sex === "male" ? "Hombre" : data.sex === "female" ? "Mujer" : null, data.age ? `${data.age} años` : null]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
          <p className="text-sm font-semibold text-muted">Nivel general</p>
          <p className="mt-0.5 text-2xl font-bold">
            {data.overall_level} <span className="text-base font-semibold text-muted">{data.overall_score}/4</span>
          </p>

          <div className="mt-3 grid grid-cols-3 gap-2">
            {(["halterofilia", "gimnasia", "metcon"] as FitCategory[]).map((cat) => (
              <div key={cat} className="rounded-xl bg-surface-2 p-2.5 text-center">
                <p className="text-xs text-muted">{CAT_LABEL[cat]}</p>
                <p className="mt-0.5 font-bold">
                  {data.category_levels[cat] ?? "—"}
                </p>
                {data.category_scores[cat] !== undefined && (
                  <p className="text-xs text-muted">{data.category_scores[cat]}/4</p>
                )}
              </div>
            ))}
          </div>
        </Card>
      ) : (
        <Card className="mb-4">
          <p className="text-sm text-muted">
            Todavía no has registrado marcas para calcular tu Fit Level. Llena el formulario de
            abajo.
          </p>
        </Card>
      )}

      <Button full onClick={() => setEditing(true)}>
        ✏️ Llenar / actualizar mis marcas
      </Button>

      <Sheet open={editing} onClose={() => setEditing(false)} title="Actualizar marcas">
        <div className="space-y-5">
          <section>
            <p className="mb-2 text-sm font-semibold text-muted">Perfil</p>
            <div className="space-y-3">
              <Field
                label={`Peso corporal (${unit})`}
                type="number"
                inputMode="decimal"
                step={unit === "lb" ? "1" : "0.5"}
                min="0"
                value={bodyWeight ? kgTo(bodyWeight, unit) : ""}
                onChange={(e) => setBodyWeight(toKg(Number(e.target.value) || 0, unit))}
              />
              <div>
                <span className="mb-1.5 block text-sm font-medium text-muted">Sexo</span>
                <Segmented<"male" | "female" | "">
                  value={sex}
                  onChange={setSex}
                  options={[
                    { value: "", label: "—" },
                    { value: "male", label: "Hombre" },
                    { value: "female", label: "Mujer" },
                  ]}
                />
              </div>
              <div>
                <span className="mb-1.5 block text-sm font-medium text-muted">
                  Categoría (WODs)
                </span>
                <Segmented<WodCategory | "">
                  value={category}
                  onChange={setCategory}
                  options={[
                    { value: "", label: "—" },
                    { value: "rx", label: "RX" },
                    { value: "scaled", label: "Scaled" },
                  ]}
                />
              </div>
              <Field
                label="Edad"
                type="number"
                inputMode="numeric"
                min="0"
                max="100"
                value={age || ""}
                onChange={(e) => setAge(Number(e.target.value) || 0)}
              />
            </div>
          </section>

          <section>
            <p className="mb-2 text-sm font-semibold text-muted">🏋️ Halterofilia (1RM en {unit})</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <span className="mb-1.5 block text-xs font-medium text-muted">Snatch</span>
                <WeightStepper valueKg={snatch} onChangeKg={setSnatch} compact />
              </div>
              <div>
                <span className="mb-1.5 block text-xs font-medium text-muted">Clean & Jerk</span>
                <WeightStepper valueKg={cleanJerk} onChangeKg={setCleanJerk} compact />
              </div>
              <div>
                <span className="mb-1.5 block text-xs font-medium text-muted">Back Squat</span>
                <WeightStepper valueKg={backSquat} onChangeKg={setBackSquat} compact />
              </div>
              <div>
                <span className="mb-1.5 block text-xs font-medium text-muted">Deadlift</span>
                <WeightStepper valueKg={deadlift} onChangeKg={setDeadlift} compact />
              </div>
            </div>
          </section>

          <section>
            <p className="mb-2 text-sm font-semibold text-muted">🤸 Gimnasia (reps máximas)</p>
            <div className="grid grid-cols-2 gap-3">
              <NumberStepper label="Dominadas estrictas" value={pullUps} onChange={setPullUps} suffix="reps" />
              <NumberStepper label="Push-ups" value={pushUps} onChange={setPushUps} suffix="reps" />
              <NumberStepper label="Muscle-ups" value={muscleUps} onChange={setMuscleUps} suffix="reps" />
              <NumberStepper label="HSPU" value={hspu} onChange={setHspu} suffix="reps" />
            </div>
          </section>

          <section>
            <p className="mb-1 text-sm font-semibold text-muted">🔥 Metcon</p>
            <p className="mb-2 text-xs text-muted">
              Fran: 21-15-9 Thrusters + Pull-ups · Grace: 30 Clean & Jerks · Cindy: AMRAP 20min ·
              Remo 2000m
            </p>
            <div className="space-y-3">
              <TimeStepper label="Fran" value={fran} onChange={setFran} />
              <TimeStepper label="Grace" value={grace} onChange={setGrace} />
              <TimeStepper label="Remo 2000m" value={row2k} onChange={setRow2k} />
              <NumberStepper label="Cindy — reps totales" value={cindy} onChange={setCindy} suffix="reps" />
            </div>
          </section>

          {save.isError && (
            <p className="text-sm font-medium text-danger">
              {save.error instanceof Error ? save.error.message : "No se pudo guardar."}
            </p>
          )}

          <Button full loading={save.isPending} onClick={handleSave}>
            💾 Guardar y calcular Fit Level
          </Button>
        </div>
      </Sheet>

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </>
  );
}

function NumberStepper({
  label,
  value,
  onChange,
  step = 1,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  suffix?: string;
}) {
  return (
    <div>
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      <Stepper value={value} onChange={onChange} step={step} min={0} suffix={suffix} compact />
    </div>
  );
}

function TimeStepper({
  label,
  value,
  onChange,
}: {
  label: string;
  value: TimeValue;
  onChange: (v: TimeValue) => void;
}) {
  return (
    <div>
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      <div className="flex items-center gap-2">
        <div className="grow">
          <Stepper
            value={value.min}
            onChange={(min) => onChange({ ...value, min })}
            min={0}
            suffix="min"
            compact
          />
        </div>
        <div className="grow">
          <Stepper
            value={value.sec}
            onChange={(sec) => onChange({ ...value, sec: Math.min(59, sec) })}
            min={0}
            max={59}
            suffix="seg"
            compact
          />
        </div>
      </div>
    </div>
  );
}
