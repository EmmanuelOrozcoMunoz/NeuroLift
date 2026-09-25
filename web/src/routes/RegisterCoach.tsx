import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { IconCheck } from "@/components/icons";
import { Button, Field } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePricing } from "@/lib/boxQueries";
import type { MessageResponse } from "@/lib/types";

/**
 * Alta de un coach independiente (sin box). Queda activo de inmediato con prueba gratis: se
 * inicia sesión solo y entra directo a su panel de atletas.
 */
export default function RegisterCoach() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { data: pricing } = usePricing();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await apiFetch<MessageResponse>("/boxes/register-coach", {
        method: "POST",
        auth: false,
        body: { full_name: fullName.trim(), email: email.trim(), password },
      });
      try {
        await login(email.trim(), password);
      } catch {
        // Respuesta genérica a propósito (no enumera correos): si el login falla, lo más
        // probable es que ese correo ya tuviera cuenta y no se creó nada nuevo.
        navigate("/login", {
          replace: true,
          state: { flash: `${response.message} Si ese correo ya tenía una cuenta, entra con tu contraseña de siempre.` },
        });
        return;
      }
      navigate("/coach/atletas", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la cuenta.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
      <p className="text-sm font-semibold tracking-[0.2em] text-brand uppercase">NeuroLift para coaches</p>
      <h1 className="mt-2 mb-1 text-3xl font-bold">Crea tu cuenta de coach</h1>
      <p className="mb-5 text-sm text-muted">
        Programa a tus atletas por tu cuenta, sin necesidad de un box. Compartes un link y se unen contigo.
      </p>

      <ul className="mb-6 space-y-2 text-sm">
        {[
          pricing ? `${pricing.trial_days} días de prueba gratis, sin tarjeta` : "Prueba gratis, sin tarjeta",
          "Mesociclos, grupos, planes y seguimiento de tus atletas",
          "Tu logo y tu color en la app de tus atletas",
        ].map((item) => (
          <li key={item} className="flex items-start gap-2">
            <IconCheck className="mt-0.5 h-4 w-4 shrink-0 text-done" />
            <span>{item}</span>
          </li>
        ))}
      </ul>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Field
          label="Tu nombre"
          hint="Así te verán tus atletas."
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

        {error && <p className="text-sm font-medium text-danger">{error}</p>}

        <Button type="submit" full loading={submitting}>
          Empezar prueba gratis
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        ¿Ya tienes cuenta?{" "}
        <Link to="/login" className="font-semibold text-brand">
          Inicia sesión
        </Link>
      </p>
      <p className="mt-2 text-center text-sm text-muted">
        ¿Tienes un box con varios coaches?{" "}
        <Link to="/registrar-box" className="font-semibold text-brand">
          Registra tu box
        </Link>
      </p>
    </div>
  );
}
