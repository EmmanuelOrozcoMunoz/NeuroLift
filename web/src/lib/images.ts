/** Formatos de imagen que se pueden subir (foto de perfil, portadas, logo del box). El servidor valida el
 *  contenido real del archivo: esto solo da una respuesta rápida en el teléfono antes de gastar la subida.
 *  HEIC/HEIF son las fotos del iPhone; el servidor las guarda como JPG. */
export const IMAGE_ACCEPT = "image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif";

export const IMAGE_FORMAT_ERROR = "Formato no permitido. Usa JPG, PNG, WEBP o HEIC.";

const TIPOS_ACEPTADOS = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"];

/** Windows y Android suelen mandar un .heic sin tipo MIME (cadena vacía): por eso también se mira la extensión. */
export function isAcceptedImage(file: { type: string; name: string }): boolean {
  if (TIPOS_ACEPTADOS.includes(file.type)) return true;
  const nombre = file.name.toLowerCase();
  return nombre.endsWith(".heic") || nombre.endsWith(".heif");
}
