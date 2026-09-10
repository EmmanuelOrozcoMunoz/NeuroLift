import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { apiFetch, setUnauthorizedHandler, tokenStore } from "@/lib/api";
import type { LoginResponse, User } from "@/lib/types";

interface AuthState {
  user: User | null;
  /** true mientras se resuelve si el token guardado sigue siendo válido. */
  loading: boolean;
  /** Mensaje a mostrar en el login cuando la sesión se cerró sola (token revocado/expirado). */
  notice: string | null;
  clearNotice: () => void;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  /** Vuelve a pedir /auth/me — se usa tras subir/borrar la foto de perfil para que
   *  `has_avatar` quede al día sin forzar un logout/login. */
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  const reset = useCallback(
    (message: string | null) => {
      tokenStore.clear();
      setUser(null);
      setNotice(message);
      queryClient.clear();
    },
    [queryClient],
  );

  // Un 401 en CUALQUIER llamada significa que el token ya no sirve: en vez de que cada
  // pantalla muestre su propio error, se cierra la sesión aquí una sola vez.
  useEffect(() => {
    setUnauthorizedHandler(() => reset("Tu sesión expiró o fue cerrada. Inicia sesión de nuevo."));
  }, [reset]);

  // Rehidratación al abrir la app: si hay token guardado, se le pregunta al backend quién es.
  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      if (!tokenStore.get()) {
        setLoading(false);
        return;
      }
      try {
        const me = await apiFetch<User>("/auth/me");
        if (!cancelled) setUser(me);
      } catch {
        // apiFetch ya limpió la sesión si fue 401; cualquier otro fallo (backend caído)
        // tampoco debe dejar la app colgada en el spinner.
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await apiFetch<LoginResponse>("/auth/login", {
        method: "POST",
        body: { email, password },
        auth: false,
      });
      // El token se guarda ANTES de pedir /auth/me: esa llamada ya necesita el header.
      tokenStore.set(access_token);
      try {
        const me = await apiFetch<User>("/auth/me");
        setUser(me);
        setNotice(null);
        return me;
      } catch (err) {
        tokenStore.clear();
        throw err;
      }
    },
    [],
  );

  const refreshUser = useCallback(async () => {
    if (!tokenStore.get()) return;
    try {
      const me = await apiFetch<User>("/auth/me");
      setUser(me);
    } catch {
      /* si el token ya no sirve, apiFetch ya disparó el logout global */
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      // Revocación real del lado del servidor (avanza token_version): invalida este token
      // y los de cualquier otro dispositivo. Si falla, la sesión local se cierra igual.
      await apiFetch<unknown>("/auth/logout", { method: "POST" });
    } catch {
      /* no-op */
    }
    reset(null);
  }, [reset]);

  const value = useMemo<AuthState>(
    () => ({ user, loading, notice, clearNotice: () => setNotice(null), login, logout, refreshUser }),
    [user, loading, notice, login, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return context;
}

/**
 * El usuario ya autenticado. Solo se usa dentro de rutas protegidas, donde el guard
 * garantiza que existe — así las pantallas no tienen que lidiar con `user | null`.
 */
export function useCurrentUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error("useCurrentUser requiere una ruta protegida");
  return user;
}
