import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";
import { useEffect, useState } from "react";

// ------------------------------------------------------------------- utilidades

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

// ---------------------------------------------------------------------- botones

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "done";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  loading?: boolean;
  full?: boolean;
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-brand text-white active:bg-brand/85 disabled:bg-brand/40",
  secondary: "bg-surface-2 text-fg border border-line active:bg-line",
  ghost: "bg-transparent text-muted active:bg-surface-2",
  danger: "bg-transparent text-danger border border-danger/40 active:bg-danger/10",
  done: "bg-done text-ink active:bg-done/85",
};

export function Button({
  variant = "primary",
  loading = false,
  full = false,
  className,
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      // min-h-12: 48px es el mínimo cómodo para el dedo
      className={cx(
        "inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 font-semibold",
        "transition-colors select-none disabled:opacity-60",
        full && "w-full",
        VARIANTS[variant],
        className,
      )}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  );
}

// -------------------------------------------------------------------- tarjetas

export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cx("rounded-2xl border border-line bg-surface p-4", className)}>{children}</div>
  );
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mt-6 mb-2 flex items-baseline justify-between gap-3">
      <h2 className="text-sm font-semibold tracking-wide text-muted uppercase">{children}</h2>
      {action}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "brand" | "done" | "warn";
}) {
  const tones = {
    neutral: "bg-surface-2 text-muted",
    brand: "bg-brand-soft text-brand",
    done: "bg-done-soft text-done",
    warn: "bg-warn/15 text-warn",
  };
  return (
    <span className={cx("rounded-full px-2.5 py-1 text-xs font-semibold", tones[tone])}>{children}</span>
  );
}

// ----------------------------------------------------------------------- inputs

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function Field({ label, hint, className, ...rest }: FieldProps) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-muted">{label}</span>
      <input
        className={cx(
          "min-h-12 w-full rounded-xl border border-line bg-surface-2 px-3.5 text-fg",
          "placeholder:text-muted/50 focus:border-brand focus:outline-none",
          className,
        )}
        {...rest}
      />
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

/**
 * Contador con botones -/+ grandes (con la barra en las manos, teclear en un input numérico
 * de celular no es viable; un tap en un botón de 48px sí) PERO el número del centro también se
 * puede tocar para escribirlo directo: para marcas altas (ej. un Back Squat de 150kg) ir
 * tap-a-tap con +1/+2.5 es incómodo. Ambos caminos quedan disponibles, cada quien usa el que le
 * convenga en el momento.
 */
export function Stepper({
  value,
  onChange,
  step = 1,
  min = 0,
  max = 9999,
  suffix,
  compact = false,
}: {
  value: number;
  onChange: (value: number) => void;
  step?: number;
  min?: number;
  max?: number;
  suffix?: string;
  compact?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  const clamp = (next: number) => Math.min(max, Math.max(min, Math.round(next * 100) / 100));

  function startEditing() {
    setDraft(value ? String(value) : "");
    setEditing(true);
  }

  function commit() {
    const parsed = Number(draft.replace(",", "."));
    if (draft.trim() !== "" && !Number.isNaN(parsed)) onChange(clamp(parsed));
    setEditing(false);
  }

  return (
    <div className="flex items-stretch overflow-hidden rounded-xl border border-line bg-surface-2">
      <button
        type="button"
        aria-label="Restar"
        className="w-10 shrink-0 text-xl font-bold text-muted active:bg-line"
        onClick={() => onChange(clamp(value - step))}
      >
        −
      </button>
      {editing ? (
        <input
          type="number"
          inputMode="decimal"
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onFocus={(e) => e.currentTarget.select()}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
            if (e.key === "Escape") setEditing(false);
          }}
          className={cx(
            "min-w-0 grow bg-transparent text-center font-bold tabular-nums outline-none",
            compact ? "text-base" : "text-lg",
          )}
        />
      ) : (
        <button
          type="button"
          onClick={startEditing}
          className={cx(
            "flex min-w-0 grow items-baseline justify-center gap-0.5 py-2.5 tabular-nums",
            compact ? "text-base" : "text-lg",
          )}
        >
          <span className="font-bold">{Number.isInteger(value) ? value : value.toFixed(1)}</span>
          {suffix && <span className="text-xs text-muted">{suffix}</span>}
        </button>
      )}
      <button
        type="button"
        aria-label="Sumar"
        className="w-10 shrink-0 text-xl font-bold text-muted active:bg-line"
        onClick={() => onChange(clamp(value + step))}
      >
        +
      </button>
    </div>
  );
}

export function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex gap-1 rounded-xl border border-line bg-surface-2 p-1">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={cx(
            "min-h-10 grow rounded-lg px-3 text-sm font-semibold transition-colors",
            option.value === value ? "bg-brand text-white" : "text-muted active:bg-line",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

// --------------------------------------------------------------- estados vacíos

export function Spinner({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={cx("animate-spin", className)} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("animate-skeleton rounded-xl bg-surface-2", className)} />;
}

export function LoadingList({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-20 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  children,
  action,
}: {
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-line px-6 py-10 text-center">
      {icon && <div className="mb-3 flex justify-center text-muted">{icon}</div>}
      <p className="font-semibold">{title}</p>
      {children && <p className="mx-auto mt-1.5 max-w-xs text-sm text-muted">{children}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message =
    error instanceof Error ? error.message : "Algo salió mal. Intenta de nuevo en un momento.";
  return (
    <div className="rounded-2xl border border-danger/30 bg-danger/5 px-5 py-6 text-center">
      <p className="font-semibold text-danger">No se pudo cargar</p>
      <p className="mt-1.5 text-sm text-muted">{message}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  );
}

/** Aviso breve fijo al pie (encima de la barra de navegación). */
export function Toast({
  message,
  tone = "done",
  onDismiss,
}: {
  message: string;
  tone?: "done" | "danger";
  onDismiss: () => void;
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 3200);
    return () => clearTimeout(timer);
  }, [message, onDismiss]);

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex justify-center px-4">
      <div
        className={cx(
          "max-w-sm rounded-xl px-4 py-3 text-sm font-semibold shadow-lg",
          tone === "done" ? "bg-done text-ink" : "bg-danger text-white",
        )}
      >
        {message}
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ hoja modal

export function Sheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <button
        type="button"
        aria-label="Cerrar"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="pb-safe relative w-full max-w-md rounded-t-3xl border-t border-line bg-surface px-5 pt-3">
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line" />
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-bold">{title}</h3>
          <button type="button" onClick={onClose} className="p-2 text-2xl leading-none text-muted">
            ×
          </button>
        </div>
        <div className="max-h-[70dvh] overflow-y-auto pb-4">{children}</div>
      </div>
    </div>
  );
}
