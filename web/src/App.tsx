import { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { useAuth, useCurrentUser } from "@/lib/auth";
import { isStandalone } from "@/lib/pwa";
import type { Role } from "@/lib/types";
import AdminLogs from "@/routes/admin/Logs";
import AdminOverview from "@/routes/admin/Overview";
import AdminUsers from "@/routes/admin/Users";
import AthleteDetail from "@/routes/coach/AthleteDetail";
import Athletes from "@/routes/coach/Athletes";
import GroupDetail from "@/routes/coach/GroupDetail";
import GroupProgramDetail from "@/routes/coach/GroupProgramDetail";
import Groups from "@/routes/coach/Groups";
import Leaderboard from "@/routes/coach/Leaderboard";
import Landing from "@/routes/Landing";
import CoachMesocycleEditor from "@/routes/coach/MesocycleEditor";
import CoachPlanEditor from "@/routes/coach/PlanEditor";
import CoachPlans from "@/routes/coach/Plans";
import CoachProfile from "@/routes/coach/Profile";
import CoachSessionEditor from "@/routes/coach/SessionEditor";
import Login from "@/routes/Login";
import MesocycleDetail from "@/routes/MesocycleDetail";
import Mesocycles from "@/routes/Mesocycles";
import MyPersonalSessionEditor from "@/routes/MyPersonalSessionEditor";
import PlanDetail from "@/routes/PlanDetail";
import Plans from "@/routes/Plans";
import Profile from "@/routes/Profile";
import Register from "@/routes/Register";
import SessionDetail from "@/routes/SessionDetail";
import Today from "@/routes/Today";

// La calculadora de Fit Level es la pantalla más pesada (14 campos + tablas de baremos) y
// la que menos se abre: va en su propio chunk.
const FitLevel = lazy(() => import("@/routes/FitLevel"));

function FullScreenLoader() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <Spinner className="h-8 w-8 text-brand" />
    </div>
  );
}

/** Cualquier usuario autenticado (atleta, coach o admin) llega hasta el shell. */
function RequireAppAccess({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <FullScreenLoader />;
  if (!user) {
    // Quien llega a la raíz sin sesión desde el navegador ve primero la landing (qué es la app,
    // instalarla, crear cuenta). Si ya la abrió instalada, eso sobra: directo al login.
    if (location.pathname === "/" && !isStandalone()) return <Navigate to="/bienvenida" replace />;
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}

function homeForRole(role: Role): string {
  if (role === "coach") return "/coach/atletas";
  if (role === "admin") return "/admin";
  return "/";
}

/** Dentro del shell, separa el árbol de rutas de atleta/coach/admin: si el rol no coincide
 *  con ninguno de los aceptados, manda al home del rol correcto en vez de mostrar un 404 o
 *  la pantalla equivocada. */
function RoleGate({ role, children }: { role: Role | Role[]; children: ReactNode }) {
  const user = useCurrentUser();
  const allowed = Array.isArray(role) ? role : [role];
  if (allowed.includes(user.role)) return <>{children}</>;
  return <Navigate to={homeForRole(user.role)} replace />;
}

function RedirectIfLogged({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

/** "/" no tiene un componente único: es el home de atleta, pero un coach o admin logueado
 *  debe mandar de una vez a su propio home en vez de mostrarle la pantalla de atleta un instante. */
function RootRoute() {
  const user = useCurrentUser();
  if (user.role !== "athlete") return <Navigate to={homeForRole(user.role)} replace />;
  return <Today />;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/bienvenida"
        element={
          <RedirectIfLogged>
            <Landing />
          </RedirectIfLogged>
        }
      />
      <Route
        path="/login"
        element={
          <RedirectIfLogged>
            <Login />
          </RedirectIfLogged>
        }
      />
      <Route
        path="/registro"
        element={
          <RedirectIfLogged>
            <Register />
          </RedirectIfLogged>
        }
      />

      <Route
        element={
          <RequireAppAccess>
            <AppShell />
          </RequireAppAccess>
        }
      >
        {/* ---------------------------------------------------------- atleta */}
        <Route path="/" element={<RootRoute />} />
        <Route
          path="/entrenos"
          element={
            <RoleGate role="athlete">
              <Mesocycles />
            </RoleGate>
          }
        />
        <Route
          path="/entrenos/:mesocycleId"
          element={
            <RoleGate role="athlete">
              <MesocycleDetail />
            </RoleGate>
          }
        />
        <Route
          path="/entrenos/:mesocycleId/sesion/:sessionId"
          element={
            <RoleGate role="athlete">
              <SessionDetail />
            </RoleGate>
          }
        />
        <Route
          path="/entrenos/:mesocycleId/sesion/:sessionId/editar"
          element={
            <RoleGate role="athlete">
              <MyPersonalSessionEditor />
            </RoleGate>
          }
        />
        <Route
          path="/planes"
          element={
            <RoleGate role="athlete">
              <Plans />
            </RoleGate>
          }
        />
        <Route
          path="/planes/:planId"
          element={
            <RoleGate role="athlete">
              <PlanDetail />
            </RoleGate>
          }
        />
        <Route
          path="/perfil"
          element={
            <RoleGate role="athlete">
              <Profile />
            </RoleGate>
          }
        />
        <Route
          path="/perfil/fit-level"
          element={
            <RoleGate role="athlete">
              <Suspense fallback={<FullScreenLoader />}>
                <FitLevel />
              </Suspense>
            </RoleGate>
          }
        />

        {/* ----------------------------------------------------------- coach */}
        <Route
          path="/coach/atletas"
          element={
            <RoleGate role="coach">
              <Athletes />
            </RoleGate>
          }
        />
        <Route
          path="/coach/actividad"
          element={
            <RoleGate role="coach">
              <Leaderboard />
            </RoleGate>
          }
        />
        <Route
          path="/coach/atletas/:athleteId"
          element={
            <RoleGate role="coach">
              <AthleteDetail />
            </RoleGate>
          }
        />
        <Route
          path="/coach/grupos"
          element={
            <RoleGate role={["coach", "admin"]}>
              <Groups />
            </RoleGate>
          }
        />
        <Route
          path="/coach/grupos/:groupId"
          element={
            <RoleGate role={["coach", "admin"]}>
              <GroupDetail />
            </RoleGate>
          }
        />
        <Route
          path="/coach/grupos/:groupId/programas/:programName/:startDate"
          element={
            <RoleGate role={["coach", "admin"]}>
              <GroupProgramDetail />
            </RoleGate>
          }
        />
        <Route
          path="/coach/mesociclos/:mesocycleId"
          element={
            <RoleGate role="coach">
              <CoachMesocycleEditor />
            </RoleGate>
          }
        />
        <Route
          path="/coach/mesociclos/:mesocycleId/sesion/:sessionId"
          element={
            <RoleGate role="coach">
              <CoachSessionEditor />
            </RoleGate>
          }
        />
        <Route
          path="/coach/planes"
          element={
            <RoleGate role="coach">
              <CoachPlans />
            </RoleGate>
          }
        />
        <Route
          path="/coach/planes/:planId"
          element={
            <RoleGate role="coach">
              <CoachPlanEditor />
            </RoleGate>
          }
        />
        <Route
          path="/coach/perfil"
          element={
            <RoleGate role="coach">
              <CoachProfile />
            </RoleGate>
          }
        />

        {/* ----------------------------------------------------------- admin */}
        <Route
          path="/admin"
          element={
            <RoleGate role="admin">
              <AdminOverview />
            </RoleGate>
          }
        />
        <Route
          path="/admin/usuarios"
          element={
            <RoleGate role="admin">
              <AdminUsers />
            </RoleGate>
          }
        />
        <Route
          path="/admin/logs"
          element={
            <RoleGate role="admin">
              <AdminLogs />
            </RoleGate>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
