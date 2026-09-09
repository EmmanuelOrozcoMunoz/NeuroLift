const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:8000";

const TOKEN_KEY = "neurolift_jwt";

/**
 * El token vive en localStorage. No es lo ideal (un XSS lo puede leer), pero el backend
 * de hoy lo entrega en el body de /auth/login y lo espera en el header Authorization.
 * Migrarlo a una cookie httpOnly requiere cambios del lado del servidor + CSRF; queda
 * anotado como el siguiente paso de seguridad, no como algo que este cliente pueda
 * arreglar solo.
 */
export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* modo privado / almacenamiento bloqueado: la sesión durará solo esta pestaña */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* no-op */
    }
  },
};

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Se dispara cuando el servidor rechaza el token (expiró, logout en otro dispositivo,
 *  o un admin revocó las sesiones). La capa de auth escucha y manda al login. */
type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler = () => {};
export function setUnauthorizedHandler(handler: UnauthorizedHandler) {
  onUnauthorized = handler;
}

function extractDetail(payload: unknown): string | null {
  if (typeof payload === "string") return payload;
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    // Los errores de validación de Pydantic llegan como una lista de objetos
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : null))
        .filter(Boolean);
      if (msgs.length) return msgs.join(" · ");
    }
  }
  return null;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  /** Las llamadas de login/registro van sin token a propósito. */
  auth?: boolean;
  signal?: AbortSignal;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, signal } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = tokenStore.get();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "Sin conexión con el servidor. Revisa tu red e intenta de nuevo.");
  }

  if (response.status === 401 && auth) {
    onUnauthorized();
    throw new ApiError(401, "Tu sesión expiró o fue cerrada. Inicia sesión de nuevo.");
  }

  if (response.status === 429) {
    throw new ApiError(429, "Demasiados intentos. Espera un momento antes de volver a intentar.");
  }

  if (!response.ok) {
    let payload: unknown = null;
    try {
      payload = await response.json();
    } catch {
      /* respuesta sin JSON */
    }
    throw new ApiError(response.status, extractDetail(payload) ?? `Error ${response.status}`, payload);
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  if (!text) return undefined as T;
  return JSON.parse(text) as T;
}
