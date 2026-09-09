import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button, Field } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import type { MessageResponse } from "@/lib/types";

export default function Register() {
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [bodyWeight, setBodyWeight] = useState("");
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
      const peso = Number(bodyWeight);
      const response = await apiFetch<MessageResponse>("/auth/register", {
        method: "POST",
        auth: false,
        body: {
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          role: "athlete",
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
        Cuenta de atleta. Si entrenas con un coach de NeuroLift, pídele que te agregue a su grupo
        después de registrarte.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
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

        <Button type="submit" full loading={submitting}>
          Crear cuenta
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        ¿Ya tienes cuenta?{" "}
        <Link to="/login" className="font-semibold text-brand">
          Inicia sesión
        </Link>
      </p>
    </div>
  );
}
