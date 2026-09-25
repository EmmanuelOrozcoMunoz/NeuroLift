import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { Button, Field } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { isStandalone } from "@/lib/pwa";

export default function Login() {
  const { login, notice, clearNotice } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Mensaje que dejó el registro ("tu cuenta fue creada, ya puedes iniciar sesión")
  const flash = (location.state as { flash?: string } | null)?.flash ?? null;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
      <div className="mb-8">
        <p className="text-sm font-semibold tracking-[0.2em] text-brand uppercase">NeuroLift</p>
        <h1 className="mt-2 text-3xl leading-tight font-bold">Tu entrenamiento, listo cuando llegas.</h1>
      </div>

      {(flash || notice) && (
        <p
          className={
            flash
              ? "mb-4 rounded-xl bg-done-soft px-4 py-3 text-sm font-medium text-done"
              : "mb-4 rounded-xl bg-warn/10 px-4 py-3 text-sm font-medium text-warn"
          }
        >
          {flash ?? notice}
        </p>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <Field
          label="Correo electrónico"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => {
            setEmail(event.target.value);
            clearNotice();
          }}
        />
        <Field
          label="Contraseña"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />

        {error && <p className="text-sm font-medium text-danger">{error}</p>}

        <Button type="submit" full loading={submitting}>
          Entrar
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        ¿Todavía no tienes cuenta?{" "}
        <Link to="/registro" className="font-semibold text-brand">
          Créala aquí
        </Link>
      </p>

      {!isStandalone() && (
        <p className="mt-3 text-center text-sm">
          <Link to="/bienvenida" className="text-muted underline-offset-4 active:underline">
            ¿Qué es NeuroLift?
          </Link>
        </p>
      )}
    </div>
  );
}
