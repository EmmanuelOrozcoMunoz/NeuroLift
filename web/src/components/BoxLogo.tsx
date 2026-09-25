import { cx } from "@/components/ui";
import { useProtectedImageUrl } from "@/lib/useImageUrl";

/**
 * Logo del box (protegido por JWT, como los avatares). Sin foto, muestra las iniciales sobre el
 * color de acento. `version` se incrementa tras subir/quitar la foto para forzar la descarga.
 */
export function BoxLogo({
  boxId,
  name,
  hasLogo,
  version = 0,
  className = "h-12 w-12",
}: {
  boxId: string;
  name: string;
  hasLogo: boolean;
  version?: number;
  className?: string;
}) {
  const url = useProtectedImageUrl(`/boxes/${boxId}/logo`, hasLogo, version);
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");

  return (
    <div
      className={cx(
        "flex shrink-0 items-center justify-center overflow-hidden rounded-xl bg-brand-soft font-bold text-brand",
        className,
      )}
    >
      {url ? <img src={url} alt="" className="h-full w-full object-cover" /> : <span>{initials}</span>}
    </div>
  );
}
