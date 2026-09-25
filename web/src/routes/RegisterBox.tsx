import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { IconCamera } from "@/components/icons";
import { Button, Field, SectionTitle } from "@/components/ui";
import { apiFetch, apiUpload } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { BoxRegisterPayload, MessageResponse } from "@/lib/types";

const MAX_BYTES = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

/**
 * Alta pública de un box. Crea el box (pendiente de aprobación) y la cuenta del dueño; luego
 * inicia sesión solo, sube la foto si eligió una, y lo lleva a su panel, donde ve el estado de
 * la solicitud y puede terminar de configurar el box mientras lo aprueban.
 */
export default function RegisterBox() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const fileRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    box_name: "",
    address: "",
    city: "",
    state: "",
    country: "México",
    owner_name: "",
    email: "",
    password: "",
  });
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!photo) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(photo);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photo]);

  const set = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: event.target.value }));

  function handlePhoto(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_BYTES) return setError("La foto no puede pesar más de 5 MB.");
    if (!ACCEPTED_TYPES.includes(file.type)) return setError("Formato no permitido. Usa JPG, PNG o WEBP.");
    setError(null);
    setPhoto(file);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (form.password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }

    setSubmitting(true);
    const optional = (value: string) => value.trim() || null;
    const payload: BoxRegisterPayload = {
      box_name: form.box_name.trim(),
      address: optional(form.address),
      city: form.city.trim(),
      state: optional(form.state),
      country: optional(form.country),
      owner_name: form.owner_name.trim(),
      email: form.email.trim(),
      password: form.password,
    };

    try {
      const response = await apiFetch<MessageResponse>("/boxes/register", { method: "POST", auth: false, body: payload });
      try {
        await login(payload.email, payload.password);
      } catch {
        // El backend responde igual exista o no el correo (no enumera cuentas). Si el login
        // falla, lo más probable es que ese correo ya tuviera una cuenta: no se creó nada.
        navigate("/login", {
          replace: true,
          state: {
            flash: `${response.message} Si ese correo ya tenía una cuenta, inicia sesión con tu contraseña de siempre.`,
          },
        });
        return;
      }
      if (photo) {
        try {
          await apiUpload("/boxes/me/logo", photo);
        } catch {
          /* la foto se puede volver a subir desde el panel del box */
        }
      }
      navigate("/box", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo registrar el box.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
      <p className="text-sm font-semibold tracking-[0.2em] text-brand uppercase">NeuroLift para boxes</p>
      <h1 className="mt-2 mb-1 text-3xl font-bold">Registra tu box</h1>
      <p className="mb-6 text-sm text-muted">
        Revisamos cada solicitud antes de activarla. Mientras tanto podrás entrar y dejar listo el perfil de tu box.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-2xl border border-dashed border-line bg-surface-2 text-muted active:bg-line"
            aria-label="Elegir foto del box"
          >
            {preview ? <img src={preview} alt="" className="h-full w-full object-cover" /> : <IconCamera className="h-7 w-7" />}
          </button>
          <div className="text-sm">
            <p className="font-semibold">Foto o logo del box</p>
            <p className="text-muted">Opcional. JPG, PNG o WEBP, hasta 5 MB.</p>
          </div>
          <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={handlePhoto} />
        </div>

        <Field label="Nombre del box" required maxLength={100} value={form.box_name} onChange={set("box_name")} />

        <SectionTitle>Dirección</SectionTitle>
        <Field label="Calle y número" autoComplete="street-address" maxLength={255} value={form.address} onChange={set("address")} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="Ciudad" autoComplete="address-level2" required maxLength={100} value={form.city} onChange={set("city")} />
          <Field label="Estado" autoComplete="address-level1" maxLength={100} value={form.state} onChange={set("state")} />
        </div>
        <Field label="País" autoComplete="country-name" maxLength={100} value={form.country} onChange={set("country")} />

        <SectionTitle>Tu cuenta de dueño</SectionTitle>
        <Field label="Tu nombre" autoComplete="name" required maxLength={100} value={form.owner_name} onChange={set("owner_name")} />
        <Field
          label="Correo electrónico"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          value={form.email}
          onChange={set("email")}
        />
        <Field
          label="Contraseña"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          hint="Mínimo 8 caracteres."
          value={form.password}
          onChange={set("password")}
        />

        {error && <p className="text-sm font-medium text-danger">{error}</p>}

        <Button type="submit" full loading={submitting}>
          Enviar solicitud
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        ¿Ya registraste tu box?{" "}
        <Link to="/login" className="font-semibold text-brand">
          Inicia sesión
        </Link>
      </p>
    </div>
  );
}
