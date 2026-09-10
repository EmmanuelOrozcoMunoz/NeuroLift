import { useRef, useState } from "react";

import { IconCamera, IconImage, IconTrash } from "@/components/icons";
import { Spinner, cx } from "@/components/ui";
import { apiFetch, apiUpload, ApiError } from "@/lib/api";
import { useProtectedImageUrl } from "@/lib/useImageUrl";
import type { MessageResponse } from "@/lib/types";

const MAX_BYTES = 5 * 1024 * 1024;
// El backend valida el "magic number" real del archivo — esto es solo para dar feedback
// rápido en el celular antes de gastar la subida; el enforcement de verdad es del servidor.
const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

/** Miniatura de solo lectura para filas de lista (grupos, planes). Sin foto, cae a un ícono. */
export function CoverThumbnail({
  coverPath,
  hasImage,
  className = "h-12 w-12 rounded-xl",
}: {
  coverPath: string;
  hasImage: boolean;
  className?: string;
}) {
  const url = useProtectedImageUrl(coverPath, hasImage);

  return (
    <div className={cx("flex shrink-0 items-center justify-center overflow-hidden bg-surface-2 text-muted", className)}>
      {url ? <img src={url} alt="" className="h-full w-full object-cover" /> : <IconImage className="h-5 w-5" />}
    </div>
  );
}

/**
 * Banner con foto de portada + controles para subir/quitar (grupo o plan). `coverPath` es a la
 * vez la ruta GET (para leerla) y DELETE (para quitarla); `uploadPath` normalmente es la misma
 * ruta por POST. `onChanged` se dispara tras subir/borrar con éxito, para que el llamador
 * invalide su query y `hasImage` quede al día en la próxima carga.
 */
export function CoverUploader({
  coverPath,
  uploadPath,
  hasImage,
  onChanged,
  label = "Foto de portada",
}: {
  coverPath: string;
  uploadPath: string;
  hasImage: boolean;
  onChanged: () => void;
  label?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [version, setVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const imageUrl = useProtectedImageUrl(coverPath, hasImage, version);

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
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
      await apiUpload(uploadPath, file);
      setVersion((v) => v + 1);
      onChanged();
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
      await apiFetch<MessageResponse>(coverPath, { method: "DELETE" });
      setVersion((v) => v + 1);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo quitar la foto.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mb-4">
      <button
        type="button"
        aria-label={hasImage ? `Cambiar ${label.toLowerCase()}` : `Agregar ${label.toLowerCase()}`}
        disabled={busy}
        onClick={() => inputRef.current?.click()}
        className="relative flex h-32 w-full items-center justify-center overflow-hidden rounded-2xl border border-line bg-surface-2 disabled:opacity-70"
      >
        {busy ? (
          <Spinner className="h-6 w-6" />
        ) : imageUrl ? (
          <img src={imageUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <span className="flex flex-col items-center gap-1 text-muted">
            <IconImage className="h-7 w-7" />
            <span className="text-xs font-semibold">Agregar {label.toLowerCase()}</span>
          </span>
        )}
        <span
          aria-hidden
          className="pointer-events-none absolute right-2 bottom-2 flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white ring-2 ring-ink"
        >
          <IconCamera className="h-4 w-4" />
        </span>
      </button>

      {/*
        Sin `capture`: ver AvatarUploader — con solo `accept`, el propio sistema operativo
        muestra el selector completo (Galería / Archivos / Cámara).
      */}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={handleFileChange}
      />

      <div className="mt-1.5 flex items-center gap-3">
        {hasImage && !busy && (
          <button
            type="button"
            onClick={() => void handleRemove()}
            className="inline-flex items-center gap-1 text-xs font-semibold text-danger active:opacity-70"
          >
            <IconTrash className="h-3.5 w-3.5" />
            Quitar
          </button>
        )}
        {error && <p className="text-xs font-medium text-danger">{error}</p>}
      </div>
    </div>
  );
}
