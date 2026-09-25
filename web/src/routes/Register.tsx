import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { IconCheck } from "@/components/icons";
import { Button, Field } from "@/components/ui";
import { ApiError, apiFetch } from "@/lib/api";
import type { MessageResponse } from "@/lib/types";

interface BoxPublicInfo {
  name: string;
  city: string | null;
}

type BoxLookup = { state: "idle" } | { state: "loading" } | { state: "ok"; box: BoxPublicInfo } | { state: "error"; message: string };

/** Los códigos tienen 8 caracteres (ver new_invite_code en el backend). */
const CODE_LENGTH = 8;

/**
 * Registro de ATLETA. Se entra con el link de invitación de un box (/registro?box=CODIGO) o
 * escribiendo el código a mano. Los coaches los da de alta el dueño de su box, y los dueños
 * registran su box en /registrar-box.
 */
export default function Register() {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [code, setCode] = useState(() => (params.get("box") ?? "").toUpperCase());
  const [lookup, setLookup] = useState<BoxLookup>({ state: "idle" });
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [bodyWeight, setBodyWeight] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Confirma a qué box se va a unir en cuanto el código tiene el largo completo
  useEffect(() => {
    const normalized = code.trim();
    if (normalized.length !== CODE_LENGTH) {
      setLookup({ state: "idle" });
      return;
    }
    const controller = new AbortController();
    setLookup({ state: "loading" });
    apiFetch<BoxPublicInfo>(`/boxes/by-code/${encodeURIComponent(normalized)}`, { auth: false, signal: controller.signal })
      .then((box) => setLookup({ state: "ok", box }))
      .catch((err) => {
        if (controller.signal.aborted) return;
        setLookup({ state: "error", message: err instanceof ApiError ? err.message : "No se pudo verificar el código." });
      });
    return () => controller.abort();
  }, [code]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (lookup.state !== "ok") {
      setError("Escribe un código de box válido para continuar.");
      return;
    }
    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    setSubmitting(true);
    try {
      const peso = Number(bodyWeight);
      const response = await apiFetch<MessageResponse>("/auth/register", {
        method: "POST",
        auth: false,
        body: {
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          invite_code: code.trim(),
          body_weight: bodyWeight && peso > 0 ? peso : null,
        },
      });
      // El backend responde con un mensaje genérico a propósito (no revela si el correo ya
      // estaba registrado), así que se muestra tal cual en el login.
      navigate("/login", {
        replace: true,
        state: { flash: response.message ?? "Listo. Inicia sesión con tu correo y contraseña." },
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la cuenta.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
      <h1 className="mb-1 text-3xl font-bold">Crear cuenta</h1>
      <p className="mb-6 text-sm text-muted">
        Únete a tu box con el código o el link que te compartió tu coach.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <Field
            label="Código de tu box"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            required
            maxLength={CODE_LENGTH}
            placeholder="Ej. K7M2QX9P"
            className="font-mono tracking-[0.2em] uppercase"
            value={code}
            onChange={(event) => setCode(event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ""))}
          />
          {lookup.state === "loading" && <p className="mt-1.5 text-xs text-muted">Buscando tu box…</p>}
          {lookup.state === "ok" && (
            <p className="mt-2 flex items-start gap-2 rounded-xl bg-done-soft px-3 py-2 text-sm font-medium text-done">
              <IconCheck className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                Te unirás a <b>{lookup.box.name}</b>
                {lookup.box.city && <span className="text-done/80"> · {lookup.box.city}</span>}
              </span>
            </p>
          )}
          {lookup.state === "error" && <p className="mt-1.5 text-xs font-medium text-danger">{lookup.message}</p>}
        </div>

        <Field
          label="Nombre completo"
          autoComplete="name"
          required
          maxLength={100}
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
        />
        <Field
          label="Correo electrónico"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <Field
          label="Contraseña"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          hint="Mínimo 8 caracteres."
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Field
          label="Peso corporal (kg)"
          type="number"
          inputMode="decimal"
          step="0.5"
          min="20"
          max="300"
          hint="Opcional. Se usa para calcular tu Fit Level."
          value={bodyWeight}
          onChange={(event) => setBodyWeight(event.target.value)}
        />

        {error && <p className="text-sm font-medium text-danger">{error}</p>}

        <Button type="submit" full loading={submitting} disabled={lookup.state !== "ok"}>
          Crear cuenta
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        ¿Ya tienes cuenta?{" "}
        <Link to="/login" className="font-semibold text-brand">
          Inicia sesión
        </Link>
      </p>
      <p className="mt-2 text-center text-sm text-muted">
        ¿Eres dueño de un box?{" "}
        <Link to="/registrar-box" className="font-semibold text-brand">
          Registra tu box
        </Link>
      </p>
    </div>
  );
}
