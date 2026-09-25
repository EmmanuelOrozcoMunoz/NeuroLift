import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import type { ComponentType, ReactNode } from "react";

import { BoxLogo } from "@/components/BoxLogo";
import {
  IconBack,
  IconDumbbell,
  IconHome,
  IconList,
  IconOffline,
  IconShield,
  IconStore,
  IconToday,
  IconTrophy,
  IconUser,
  IconUsers,
  Logo,
} from "@/components/icons";
import { cx } from "@/components/ui";
import { useCurrentUser } from "@/lib/auth";
import type { User } from "@/lib/types";

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

const ATHLETE_NAV: NavItem[] = [
  { to: "/", label: "Hoy", icon: IconToday },
  { to: "/entrenos", label: "Entrenos", icon: IconDumbbell },
  { to: "/planes", label: "Planes", icon: IconStore },
  { to: "/perfil", label: "Perfil", icon: IconUser },
];

const COACH_NAV: NavItem[] = [
  { to: "/coach/atletas", label: "Atletas", icon: IconUsers },
  { to: "/coach/actividad", label: "Actividad", icon: IconTrophy },
  { to: "/coach/grupos", label: "Grupos", icon: IconDumbbell },
  { to: "/coach/planes", label: "Planes", icon: IconStore },
  { to: "/coach/perfil", label: "Perfil", icon: IconUser },
];

const OWNER_NAV: NavItem[] = [
  { to: "/box", label: "Box", icon: IconHome },
  { to: "/coach/atletas", label: "Atletas", icon: IconUsers },
  { to: "/coach/grupos", label: "Grupos", icon: IconDumbbell },
  { to: "/coach/planes", label: "Planes", icon: IconStore },
  { to: "/coach/perfil", label: "Perfil", icon: IconUser },
];

// Coach independiente: la barra de un coach, con "Cuenta" (plan, link de invitación, marca)
const INDEPENDENT_COACH_NAV: NavItem[] = [
  { to: "/coach/atletas", label: "Atletas", icon: IconUsers },
  { to: "/coach/grupos", label: "Grupos", icon: IconDumbbell },
  { to: "/coach/planes", label: "Planes", icon: IconStore },
  { to: "/box", label: "Cuenta", icon: IconHome },
  { to: "/coach/perfil", label: "Perfil", icon: IconUser },
];

// Con el box pendiente o suspendido, el dueño solo tiene su panel y su perfil
const OWNER_INACTIVE_NAV: NavItem[] = [
  { to: "/box", label: "Box", icon: IconHome },
  { to: "/coach/perfil", label: "Perfil", icon: IconUser },
];

const ADMIN_NAV: NavItem[] = [
  { to: "/admin", label: "Resumen", icon: IconShield },
  { to: "/admin/boxes", label: "Cuentas", icon: IconHome },
  { to: "/admin/usuarios", label: "Usuarios", icon: IconUsers },
  { to: "/coach/grupos", label: "Grupos", icon: IconDumbbell },
  { to: "/admin/logs", label: "Logs", icon: IconList },
];

function navFor(user: User): NavItem[] {
  if (user.role === "coach") return COACH_NAV;
  if (user.role === "admin") return ADMIN_NAV;
  if (user.role === "owner") {
    if (user.box?.status !== "active") return OWNER_INACTIVE_NAV;
    return user.box.kind === "coach" ? INDEPENDENT_COACH_NAV : OWNER_NAV;
  }
  return ATHLETE_NAV;
}

// Rutas "raíz" de sección: solo se marcan activas en su URL exacta, no en sus subrutas
const EXACT_ROUTES = new Set(["/", "/admin", "/box"]);

const ROLE_LABEL: Record<User["role"], string> = {
  athlete: "Atleta",
  coach: "Coach",
  owner: "Dueño",
  admin: "Admin de plataforma",
};

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
    // Sin borde: el difuminado del fondo basta para separarlo del contenido que pasa debajo
    <header className="pt-safe sticky top-0 z-30 -mx-4 mb-5 bg-ink/85 px-4 backdrop-blur-xl lg:-mx-8 lg:px-8">
      <div className="flex min-h-16 items-center gap-2 py-2">
        {back && (
          <button
            type="button"
            aria-label="Volver"
            className="press -ml-3 flex h-touch w-touch shrink-0 items-center justify-center rounded-full text-muted active:bg-surface"
            onClick={() => (typeof back === "string" ? navigate(back) : navigate(-1))}
          >
            <IconBack className="h-6 w-6" />
          </button>
        )}
        <div className="min-w-0 grow">
          <h1 className="truncate text-2xl leading-tight font-extrabold tracking-tight">{title}</h1>
          {subtitle && <p className="truncate text-sm text-muted">{subtitle}</p>}
        </div>
        {action}
      </div>
    </header>
  );
}

/** Pestaña de la barra inferior (móvil): ícono con "píldora" de fondo cuando está activa. */
function TabItem({ item }: { item: NavItem }) {
  const { to, label, icon: Icon } = item;
  return (
    <NavLink
      to={to}
      end={EXACT_ROUTES.has(to)}
      className={({ isActive }) =>
        cx(
          "flex min-h-touch grow basis-0 flex-col items-center justify-center gap-1 pt-2 pb-1",
          "text-[11px] font-semibold transition-colors",
          isActive ? "text-fg" : "text-muted",
        )
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={cx(
              "flex h-8 w-14 items-center justify-center rounded-full transition-colors duration-200",
              isActive ? "bg-surface-2" : "bg-transparent",
            )}
          >
            <Icon className="h-6 w-6" />
          </span>
          {label}
        </>
      )}
    </NavLink>
  );
}

/** Fila del sidebar (escritorio). */
function SideItem({ item }: { item: NavItem }) {
  const { to, label, icon: Icon } = item;
  return (
    <NavLink
      to={to}
      end={EXACT_ROUTES.has(to)}
      className={({ isActive }) =>
        cx(
          "press flex min-h-touch items-center gap-3 rounded-xl px-3 font-semibold transition-colors",
          isActive ? "bg-surface text-fg" : "text-muted hover:bg-surface/60 hover:text-fg",
        )
      }
    >
      <Icon className="h-5 w-5 shrink-0" />
      {label}
    </NavLink>
  );
}

/** Identidad de la cuenta en el sidebar: el box / coach del usuario, o NeuroLift para el admin. */
function SidebarBrand({ user }: { user: User }) {
  if (!user.box) {
    return (
      <div className="flex items-center gap-3">
        <Logo className="h-10 w-10" />
        <span className="text-lg font-extrabold tracking-tight">NeuroLift</span>
      </div>
    );
  }
  return (
    <div className="flex min-w-0 items-center gap-3">
      <BoxLogo boxId={user.box.id} name={user.box.name} hasLogo={user.box.has_logo} className="h-10 w-10 text-sm" />
      <div className="min-w-0">
        <p className="truncate font-extrabold tracking-tight">{user.box.name}</p>
        <p className="label-caps">NeuroLift</p>
      </div>
    </div>
  );
}

export function AppShell() {
  const online = useOnline();
  const user = useCurrentUser();
  const navItems = navFor(user);

  return (
    <div className="min-h-dvh">
      {/* Primer elemento enfocable: el teclado salta la navegación directo al contenido */}
      <a
        href="#contenido"
        className="sr-only z-50 rounded-xl bg-brand px-4 py-3 font-semibold text-on-brand focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Saltar al contenido
      </a>

      {!online && (
        <div
          role="status"
          className="pt-safe fixed inset-x-0 top-0 z-40 flex items-center justify-center gap-2 bg-warn-soft py-1.5 text-xs font-semibold text-warn lg:left-sidebar"
        >
          <IconOffline className="h-4 w-4" />
          Sin conexión — puedes ver lo ya cargado
        </div>
      )}

      {/* ------------------------------------------------ sidebar (escritorio) */}
      <aside className="pt-safe fixed inset-y-0 left-0 z-30 hidden w-sidebar flex-col gap-8 bg-ink px-4 py-6 lg:flex">
        <SidebarBrand user={user} />
        <nav aria-label="Principal" className="flex flex-col gap-1">
          {navItems.map((item) => (
            <SideItem key={item.to} item={item} />
          ))}
        </nav>
        <div className="mt-auto min-w-0 px-3">
          <p className="truncate text-sm font-semibold">{user.full_name}</p>
          <p className="truncate text-xs text-muted">{ROLE_LABEL[user.role]}</p>
        </div>
      </aside>

      {/* ------------------------------------------------------- contenido */}
      <div className="lg:pl-sidebar">
        <main
          id="contenido"
          tabIndex={-1}
          className={cx(
            "pr-safe pl-safe mx-auto w-full max-w-md px-4 outline-none",
            // Móvil: aire para la barra inferior fija (+ indicador de gestos del iPhone)
            "pb-[calc(var(--spacing-tabbar)+env(safe-area-inset-bottom)+1.5rem)]",
            "lg:max-w-2xl lg:px-8 lg:pb-12",
          )}
        >
          <Outlet />
        </main>
      </div>

      {/* --------------------------------------- barra inferior (móvil/tablet) */}
      <nav
        aria-label="Principal"
        className="pb-safe fixed inset-x-0 bottom-0 z-30 bg-ink/90 backdrop-blur-xl lg:hidden"
      >
        <div className="mx-auto flex h-tabbar max-w-md items-stretch px-2">
          {navItems.map((item) => (
            <TabItem key={item.to} item={item} />
          ))}
        </div>
      </nav>
    </div>
  );
}
