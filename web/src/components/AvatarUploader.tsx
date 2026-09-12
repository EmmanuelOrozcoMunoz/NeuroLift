import { useRef, useState } from "react";

import { IconCamera, IconTrash, IconUser } from "@/components/icons";
import { Spinner, cx } from "@/components/ui";
import { apiFetch, apiUpload, ApiError } from "@/lib/api";
import { useAuth, useCurrentUser } from "@/lib/auth";
import { monthYear } from "@/lib/dates";
import { useAvatarUrl } from "@/lib/useAvatarUrl";
import type { MessageResponse, User } from "@/lib/types";

const MAX_BYTES = 5 * 1024 * 1024;
// El backend valida el "magic number" real del archivo — esto es solo para dar feedback
// rápido en el celular antes de gastar la subida; el enforcement de verdad es del servidor.
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

export function AvatarUploader() {
  const user = useCurrentUser();
  const { refreshUser } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);

  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const photoUrl = useAvatarUrl(user.id, user.has_avatar, version);
  const initials = user.full_name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // permite volver a elegir el mismo archivo después
    if (!file) return;

    setError(null);

    if (file.size > MAX_BYTES) {
      setError("La imagen no puede pesar más de 5 MB.");
      return;
    }
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError("Formato no permitido. Usa JPG, PNG o WEBP.");
      return;
    }

    setBusy(true);
    try {
      await apiUpload<User>("/users/me/avatar", file);
      await refreshUser();
      setVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo subir la foto.");
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove() {
    setBusy(true);
    setError(null);
    try {
      await apiFetch<MessageResponse>("/users/me/avatar", { method: "DELETE" });
      await refreshUser();
      setVersion((v) => v + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo quitar la foto.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-4">
      <div className="relative shrink-0">
        {/* Todo el círculo es clicable (no solo el badge de cámara): en un celular es un
            blanco de toque mucho más cómodo que un botoncito de 32px. */}
        <button
          type="button"
          aria-label="Elegir foto de perfil"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className={cx(
            "flex h-20 w-20 items-center justify-center overflow-hidden rounded-full",
            "bg-brand-soft text-brand ring-2 ring-line disabled:opacity-70",
          )}
        >
          {busy ? (
            <Spinner className="h-6 w-6" />
          ) : photoUrl ? (
            <img src={photoUrl} alt="" className="h-full w-full object-cover" />
          ) : initials ? (
            <span className="text-2xl font-bold">{initials}</span>
          ) : (
            <IconUser className="h-9 w-9" />
          )}
        </button>

        <div
          aria-hidden
          className="pointer-events-none absolute -right-1 -bottom-1 flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white ring-2 ring-ink"
        >
          <IconCamera className="h-4 w-4" />
        </div>

        {/*
          Sin `capture`: en varios navegadores de Android, poner capture="environment" (o
          "user") ABRE LA CÁMARA DIRECTAMENTE y no deja elegir una foto ya existente de la
          galería. Dejando solo `accept`, el propio sistema operativo muestra el selector
          completo (Galería / Archivos / Cámara) tanto en Android como en iOS, y en
          escritorio abre el diálogo normal de "Elegir archivo".
        */}
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handleFileChange}
        />
      </div>

      <div className="min-w-0 grow">
        <p className="truncate font-bold">{user.full_name}</p>
        <p className="truncate text-sm text-muted">{user.email}</p>
        {user.created_at && (
          <p className="truncate text-xs text-muted">Miembro desde {monthYear(user.created_at)}</p>
        )}
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="mt-1 text-xs font-semibold text-brand active:opacity-70 disabled:opacity-50"
        >
          {user.has_avatar ? "Cambiar foto" : "Elegir foto"}
        </button>
        {user.has_avatar && !busy && (
          <button
            type="button"
            onClick={() => void handleRemove()}
            className="mt-1 ml-3 inline-flex items-center gap-1 text-xs font-semibold text-danger active:opacity-70"
          >
            <IconTrash className="h-3.5 w-3.5" />
            Quitar
          </button>
        )}
        {error && <p className="mt-1 text-xs font-medium text-danger">{error}</p>}
      </div>
    </div>
  );
}
