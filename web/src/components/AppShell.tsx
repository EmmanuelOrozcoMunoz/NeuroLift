import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import {
  IconBack,
  IconDumbbell,
  IconOffline,
  IconStore,
  IconToday,
  IconTrophy,
  IconUser,
  IconUsers,
} from "@/components/icons";
import { cx } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";

const ATHLETE_NAV = [
  { to: "/", label: "Hoy", icon: IconToday },
  { to: "/entrenos", label: "Entrenos", icon: IconDumbbell },
  { to: "/planes", label: "Planes", icon: IconStore },
  { to: "/perfil", label: "Perfil", icon: IconUser },
];

const COACH_NAV = [
  { to: "/coach/atletas", label: "Atletas", icon: IconUsers },
  { to: "/coach/actividad", label: "Actividad", icon: IconTrophy },
  { to: "/coach/grupos", label: "Grupos", icon: IconDumbbell },
  { to: "/coach/planes", label: "Planes", icon: IconStore },
  { to: "/coach/perfil", label: "Perfil", icon: IconUser },
];

function useOnline(): boolean {
  const [online, setOnline] = useState(() => navigator.onLine);

  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  return online;
}

/** Encabezado de pantalla. Cada ruta pone el suyo para no plumbear títulos por el shell. */
export function PageHeader({
  title,
  subtitle,
  back,
  action,
}: {
  title: string;
  subtitle?: string;
  /** Muestra la flecha de volver. `true` = history.back, o una ruta concreta. */
  back?: boolean | string;
  action?: ReactNode;
}) {
  const navigate = useNavigate();

  return (
    <header className="pt-safe sticky top-0 z-30 -mx-4 mb-4 border-b border-line/60 bg-ink/85 px-4 backdrop-blur-md">
      <div className="flex min-h-14 items-center gap-2 py-2">
        {back && (
          <button
            type="button"
            aria-label="Volver"
            className="-ml-2 rounded-lg p-2 text-muted active:bg-surface-2"
            onClick={() => (typeof back === "string" ? navigate(back) : navigate(-1))}
          >
            <IconBack className="h-6 w-6" />
          </button>
        )}
        <div className="min-w-0 grow">
          <h1 className="truncate text-xl leading-tight font-bold">{title}</h1>
          {subtitle && <p className="truncate text-sm text-muted">{subtitle}</p>}
        </div>
        {action}
      </div>
    </header>
  );
}

export function AppShell() {
  const online = useOnline();
  const user = useCurrentUser();
  const navItems = user.role === "coach" ? COACH_NAV : ATHLETE_NAV;

  return (
    <div className="mx-auto min-h-dvh max-w-md px-4">
      {!online && (
        <div className="pt-safe fixed inset-x-0 top-0 z-40 flex items-center justify-center gap-2 bg-warn/15 py-1.5 text-xs font-semibold text-warn">
          <IconOffline className="h-4 w-4" />
          Sin conexión — puedes ver lo ya cargado
        </div>
      )}

      {/* pb-28: deja aire para la barra inferior fija */}
      <main className="pb-28">
        <Outlet />
      </main>

      <nav className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-line bg-ink/95 backdrop-blur-md">
        <div className="mx-auto flex max-w-md">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cx(
                  "flex grow flex-col items-center gap-1 pt-2.5 pb-1.5 text-[11px] font-semibold",
                  isActive ? "text-brand" : "text-muted",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={cx("h-6 w-6", isActive && "scale-105")} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
