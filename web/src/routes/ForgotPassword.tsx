import { useState } from "react";
import { Link } from "react-router-dom";

import { Button, Field } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import type { MessageResponse } from "@/lib/types";

/** Pide el enlace para restablecer la contraseña. La respuesta es la misma exista o no la cuenta. */
export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const r = await apiFetch<MessageResponse>("/auth/forgot-password", {
        method: "POST",
        body: { email: email.trim() },
        auth: false,
      });
      setEnviado(r.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo enviar el correo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
      <p className="text-sm font-semibold tracking-[0.2em] text-brand uppercase">NeuroLift</p>
      <h1 className="mt-2 text-3xl leading-tight font-bold">Recupera tu contraseña</h1>

      {enviado ? (
        <>
          <p className="mt-4 rounded-xl bg-done-soft px-4 py-3 text-sm font-medium text-done">{enviado}</p>
          <p className="mt-3 text-sm text-muted">Revisa también la carpeta de spam. El enlace vence en 1 hora.</p>
        </>
      ) : (
        <>
          <p className="mt-2 mb-6 text-sm text-muted">
            Escribe tu correo y te enviamos un enlace para elegir una contraseña nueva.
          </p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field
              label="Correo electrónico"
              type="email"
              inputMode="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            {error && <p className="text-sm font-medium text-danger">{error}</p>}
            <Button type="submit" full loading={enviando}>
              Enviarme el enlace
            </Button>
          </form>
        </>
      )}

      <p className="mt-6 text-center text-sm">
        <Link to="/login" className="font-semibold text-brand">
          Volver a iniciar sesión
        </Link>
      </p>
    </div>
  );
}
