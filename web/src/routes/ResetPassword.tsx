import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Button, Field } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import type { MessageResponse } from "@/lib/types";

/** Elige la contraseña nueva con el enlace del correo (/restablecer?token=...). */
export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  // El token se guarda en memoria y se borra de la barra de direcciones: así no queda en el historial
  // ni viaja en el Referer.
  const [token] = useState(() => params.get("token") ?? "");
  useEffect(() => {
    if (params.has("token")) navigate("/restablecer", { replace: true });
  }, [params, navigate]);

  const [password, setPassword] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (password !== repetida) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setGuardando(true);
    try {
      const r = await apiFetch<MessageResponse>("/auth/reset-password", {
        method: "POST",
        body: { token, password },
        auth: false,
      });
      navigate("/login", { replace: true, state: { flash: r.message } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cambiar la contraseña.");
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
      <p className="text-sm font-semibold tracking-[0.2em] text-brand uppercase">NeuroLift</p>
      <h1 className="mt-2 text-3xl leading-tight font-bold">Elige tu contraseña nueva</h1>

      {!token ? (
        <p className="mt-4 rounded-xl bg-warn/10 px-4 py-3 text-sm font-medium text-warn">
          Este enlace no es válido. Pide uno nuevo desde "¿Olvidaste tu contraseña?".
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <Field
            label="Contraseña nueva"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Field
            label="Repite la contraseña"
            type="password"
            autoComplete="new-password"
            required
            value={repetida}
            onChange={(event) => setRepetida(event.target.value)}
          />
          {error && <p className="text-sm font-medium text-danger">{error}</p>}
          <Button type="submit" full loading={guardando}>
            Guardar contraseña
          </Button>
          <p className="text-xs text-muted">Al guardarla se cierran tus sesiones abiertas en otros dispositivos.</p>
        </form>
      )}

      <p className="mt-6 text-center text-sm">
        <Link to="/recuperar" className="text-muted underline-offset-4 active:underline">
          Pedir un enlace nuevo
        </Link>
      </p>
    </div>
  );
}
