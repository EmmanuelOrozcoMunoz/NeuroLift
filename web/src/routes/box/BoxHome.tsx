import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { CSSProperties, ReactNode } from "react";

import { PageHeader } from "@/components/AppShell";
import { BoxLogo } from "@/components/BoxLogo";
import { IconCamera, IconCheck, IconChevronRight, IconClock, IconShare, IconTrophy, IconUsers } from "@/components/icons";
import { Badge, Button, Card, ErrorState, Field, LoadingList, SectionTitle, Toast, cx } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { accentPreviewVars, DEFAULT_ACCENT } from "@/lib/brand";
import { useDeleteBoxLogo, useMyBox, useRotateInviteCode, useUpdateBox, useUploadBoxLogo } from "@/lib/boxQueries";
import type { BoxDetail, BoxStatus } from "@/lib/types";

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

// Todos con contraste suficiente sobre el fondo carbón (ver applyAccent)
const ACCENT_PRESETS = ["#ff4700", "#ef4444", "#f59e0b", "#facc15", "#84cc16", "#22c55e", "#14b8a6", "#38bdf8", "#818cf8", "#e879f9"];

const STATUS_COPY: Record<Exclude<BoxStatus, "active">, { title: string; body: string }> = {
  pending: {
    title: "Tu solicitud está en revisión",
    body: "Te avisaremos cuando tu box quede activo. Mientras tanto, deja listos la foto, la dirección y el color de tu marca.",
  },
  rejected: {
    title: "Tu solicitud no fue aprobada",
    body: "Si crees que es un error, contáctanos para revisarla de nuevo.",
  },
  suspended: {
    title: "Tu box está suspendido",
    body: "Tus coaches y atletas no pueden entrar por ahora. Contáctanos para reactivarlo.",
  },
};

type ToastState = { message: string; tone: "done" | "danger" } | null;

export default function BoxHome() {
  const { data: box, isPending, error, refetch } = useMyBox();
  const [toast, setToast] = useState<ToastState>(null);
  const notify = (message: string, tone: "done" | "danger" = "done") => setToast({ message, tone });

  if (isPending) return <LoadingList rows={4} />;
  if (error || !box) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const active = box.status === "active";
  const statusCopy = box.status === "active" ? null : STATUS_COPY[box.status];

  return (
    <>
      <PageHeader title={box.name} subtitle={[box.city, box.state].filter(Boolean).join(", ") || "Mi box"} />

      {statusCopy && (
        <Card className={cx("mb-4", box.status === "pending" ? "border-warn/40" : "border-danger/40")}>
          <div className="flex gap-3">
            <IconClock className={cx("h-6 w-6 shrink-0", box.status === "pending" ? "text-warn" : "text-danger")} />
            <div>
              <p className="font-bold">{statusCopy.title}</p>
              <p className="mt-1 text-sm text-muted">{statusCopy.body}</p>
            </div>
          </div>
        </Card>
      )}

      <LogoCard box={box} onToast={notify} />

      {active && (
        <>
          <InviteCard box={box} onToast={notify} />
          <div className="mt-4 space-y-2">
            <NavRow to="/box/equipo" icon={<IconUsers />} title="Coaches y atletas" subtitle="Da de alta coaches y asigna atletas" />
            <NavRow to="/coach/grupos" icon={<IconCheck />} title="Grupos y mesociclos generales" subtitle="Programa a los atletas sin coach" />
            <NavRow to="/coach/actividad" icon={<IconTrophy />} title="Actividad del box" subtitle="Quién entrenó esta semana" />
          </div>
        </>
      )}

      <ProfileForm box={box} onToast={notify} />
      <AccentPicker box={box} onToast={notify} />

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={() => setToast(null)} />}
    </>
  );
}

type ToastFn = (message: string, tone?: "done" | "danger") => void;

function NavRow({ to, icon, title, subtitle }: { to: string; icon: ReactNode; title: string; subtitle: string }) {
  return (
    <Link to={to} className="flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 active:bg-surface-2">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand [&>svg]:h-5 [&>svg]:w-5">
        {icon}
      </span>
      <span className="min-w-0 grow">
        <span className="block font-semibold">{title}</span>
        <span className="block truncate text-sm text-muted">{subtitle}</span>
      </span>
      <IconChevronRight className="h-5 w-5 text-muted" />
    </Link>
  );
}

function LogoCard({ box, onToast }: { box: BoxDetail; onToast: ToastFn }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [version, setVersion] = useState(0);
  const upload = useUploadBoxLogo();
  const remove = useDeleteBoxLogo();
  const busy = upload.isPending || remove.isPending;

  function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_BYTES) return onToast("La foto no puede pesar más de 5 MB.", "danger");
    if (!ACCEPTED_TYPES.includes(file.type)) return onToast("Formato no permitido. Usa JPG, PNG o WEBP.", "danger");
    upload.mutate(file, {
      onSuccess: () => {
        setVersion((v) => v + 1);
        onToast("Foto del box actualizada.");
      },
      onError: (err) => onToast(err instanceof ApiError ? err.message : "No se pudo subir la foto.", "danger"),
    });
  }

  return (
    <Card className="mb-4">
      <div className="flex items-center gap-4">
        <button
          type="button"
          aria-label="Cambiar foto del box"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="relative shrink-0 disabled:opacity-70"
        >
          <BoxLogo boxId={box.id} name={box.name} hasLogo={box.has_logo} version={version} className="h-20 w-20 text-2xl" />
          <span className="absolute -right-1 -bottom-1 flex h-8 w-8 items-center justify-center rounded-full bg-brand text-on-brand ring-2 ring-surface">
            <IconCamera className="h-4 w-4" />
          </span>
        </button>
        <div className="min-w-0">
          <p className="truncate font-bold">{box.name}</p>
          <p className="text-sm text-muted">La ven tus coaches y atletas en la app.</p>
          <div className="mt-1 flex gap-3 text-xs font-semibold">
            <button type="button" disabled={busy} onClick={() => inputRef.current?.click()} className="text-brand disabled:opacity-50">
              {box.has_logo ? "Cambiar foto" : "Subir foto"}
            </button>
            {box.has_logo && (
              <button
                type="button"
                disabled={busy}
                className="text-danger disabled:opacity-50"
                onClick={() =>
                  remove.mutate(undefined, {
                    onSuccess: () => {
                      setVersion((v) => v + 1);
                      onToast("Foto eliminada.");
                    },
                  })
                }
              >
                Quitar
              </button>
            )}
          </div>
        </div>
      </div>
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handleFile} />
    </Card>
  );
}

function InviteCard({ box, onToast }: { box: BoxDetail; onToast: ToastFn }) {
  const rotate = useRotateInviteCode();
  const link = `${window.location.origin}/registro?box=${box.invite_code ?? ""}`;
  const canShare = typeof navigator.share === "function";

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      onToast("Link copiado.");
    } catch {
      onToast("No se pudo copiar. Mantén presionado el link para copiarlo.", "danger");
    }
  }

  async function share() {
    try {
      await navigator.share({ title: `Únete a ${box.name}`, text: `Crea tu cuenta en ${box.name} con este link:`, url: link });
    } catch {
      /* el usuario canceló */
    }
  }

  return (
    <Card>
      <p className="font-bold">Invita a tus atletas</p>
      <p className="mt-1 text-sm text-muted">Con este link crean su cuenta directo en tu box. También pueden escribir el código.</p>
      <div className="mt-3 rounded-xl bg-surface-2 p-3 text-center">
        <p className="font-mono text-2xl font-bold tracking-[0.3em] text-brand">{box.invite_code}</p>
        <p className="mt-1 truncate text-xs text-muted select-all">{link}</p>
      </div>
      <div className="mt-3 flex gap-2">
        {canShare && (
          <Button className="grow" onClick={() => void share()}>
            <IconShare className="h-5 w-5" />
            Compartir
          </Button>
        )}
        <Button variant={canShare ? "secondary" : "primary"} className="grow" onClick={() => void copy()}>
          Copiar link
        </Button>
      </div>
      <button
        type="button"
        disabled={rotate.isPending}
        className="mt-3 w-full text-center text-xs font-semibold text-muted active:text-fg disabled:opacity-50"
        onClick={() => {
          if (!window.confirm("El link y el código actuales dejarán de funcionar. ¿Generar uno nuevo?")) return;
          rotate.mutate(undefined, { onSuccess: () => onToast("Nuevo código generado.") });
        }}
      >
        Generar un código nuevo
      </button>
    </Card>
  );
}

function ProfileForm({ box, onToast }: { box: BoxDetail; onToast: ToastFn }) {
  const update = useUpdateBox();
  const [form, setForm] = useState({
    name: box.name,
    address: box.address ?? "",
    city: box.city ?? "",
    state: box.state ?? "",
    country: box.country ?? "",
  });
  const set = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: event.target.value }));
  const dirty =
    form.name !== box.name ||
    form.address !== (box.address ?? "") ||
    form.city !== (box.city ?? "") ||
    form.state !== (box.state ?? "") ||
    form.country !== (box.country ?? "");

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const optional = (value: string) => value.trim() || null;
    update.mutate(
      {
        name: form.name.trim(),
        address: optional(form.address),
        city: optional(form.city),
        state: optional(form.state),
        country: optional(form.country),
      },
      {
        onSuccess: () => onToast("Datos del box guardados."),
        onError: (err) => onToast(err instanceof Error ? err.message : "No se pudo guardar.", "danger"),
      },
    );
  }

  return (
    <>
      <SectionTitle>Datos del box</SectionTitle>
      <Card>
        <form onSubmit={handleSubmit} className="space-y-3">
          <Field label="Nombre" required minLength={2} maxLength={100} value={form.name} onChange={set("name")} />
          <Field label="Calle y número" maxLength={255} value={form.address} onChange={set("address")} />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Ciudad" maxLength={100} value={form.city} onChange={set("city")} />
            <Field label="Estado" maxLength={100} value={form.state} onChange={set("state")} />
          </div>
          <Field label="País" maxLength={100} value={form.country} onChange={set("country")} />
          <Button type="submit" full disabled={!dirty} loading={update.isPending}>
            Guardar datos
          </Button>
        </form>
      </Card>
    </>
  );
}

function AccentPicker({ box, onToast }: { box: BoxDetail; onToast: ToastFn }) {
  const update = useUpdateBox();
  const saved = box.accent_color ?? DEFAULT_ACCENT;
  const [draft, setDraft] = useState(saved);
  useEffect(() => setDraft(saved), [saved]);

  const preview = accentPreviewVars(draft);
  const dirty = draft.toLowerCase() !== saved.toLowerCase();

  function save(value: string) {
    update.mutate(
      { accent_color: value === DEFAULT_ACCENT ? "" : value },
      {
        onSuccess: () => onToast("Color de marca aplicado en toda la app."),
        onError: (err) => onToast(err instanceof Error ? err.message : "No se pudo guardar el color.", "danger"),
      },
    );
  }

  return (
    <>
      <SectionTitle>Color de tu marca</SectionTitle>
      <Card>
        <p className="text-sm text-muted">Se usa en botones, pestañas y resaltados para todos los miembros de tu box.</p>
        <div className="mt-3 flex flex-wrap gap-2.5">
          {ACCENT_PRESETS.map((color) => (
            <button
              key={color}
              type="button"
              aria-label={`Color ${color}`}
              onClick={() => setDraft(color)}
              className={cx(
                "flex h-10 w-10 items-center justify-center rounded-full ring-offset-2 ring-offset-surface",
                draft.toLowerCase() === color && "ring-2 ring-fg",
              )}
              style={{ backgroundColor: color }}
            >
              {draft.toLowerCase() === color && <IconCheck className="h-5 w-5 text-ink" />}
            </button>
          ))}
          <label className="flex h-10 cursor-pointer items-center gap-2 rounded-full border border-line bg-surface-2 px-3 text-sm font-semibold">
            <input
              type="color"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              className="h-6 w-6 cursor-pointer rounded-full border-0 bg-transparent p-0"
            />
            Otro
          </label>
        </div>

        {/* Vista previa con el color elegido, sin aplicarlo todavía al resto de la app */}
        <div className="mt-4 rounded-xl border border-line bg-ink p-3" style={(preview ?? undefined) as CSSProperties | undefined}>
          {preview ? (
            <div className="flex items-center gap-3">
              <span className="rounded-xl bg-brand px-4 py-2.5 text-sm font-semibold text-on-brand">Guardar serie</span>
              <span className="text-sm font-semibold text-brand">Hoy</span>
              <Badge tone="neutral">
                <span className="text-brand">75% 1RM</span>
              </Badge>
            </div>
          ) : (
            <p className="text-sm font-medium text-danger">
              Ese color es muy oscuro: casi no se vería sobre el fondo de la app. Elige uno más claro.
            </p>
          )}
        </div>

        <div className="mt-3 flex gap-2">
          <Button className="grow" disabled={!dirty || !preview} loading={update.isPending} onClick={() => save(draft)}>
            Aplicar color
          </Button>
          {box.accent_color && (
            <Button variant="secondary" disabled={update.isPending} onClick={() => save(DEFAULT_ACCENT)}>
              Restablecer
            </Button>
          )}
        </div>
      </Card>
    </>
  );
}
