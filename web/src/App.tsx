import { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { Button, Spinner } from "@/components/ui";
import { useAuth, useCurrentUser } from "@/lib/auth";
import type { Role } from "@/lib/types";
import AthleteDetail from "@/routes/coach/AthleteDetail";
import Athletes from "@/routes/coach/Athletes";
import GroupDetail from "@/routes/coach/GroupDetail";
import GroupProgramDetail from "@/routes/coach/GroupProgramDetail";
import Groups from "@/routes/coach/Groups";
import CoachMesocycleEditor from "@/routes/coach/MesocycleEditor";
import CoachPlanEditor from "@/routes/coach/PlanEditor";
import CoachPlans from "@/routes/coach/Plans";
import CoachProfile from "@/routes/coach/Profile";
import CoachSessionEditor from "@/routes/coach/SessionEditor";
import Login from "@/routes/Login";
import MesocycleDetail from "@/routes/MesocycleDetail";
import Mesocycles from "@/routes/Mesocycles";
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

/** Cualquier usuario autenticado con rol soportado (atleta o coach) llega hasta el shell.
 *  Admin sigue operando solo desde el panel de escritorio: se le muestra el aviso, sin la
 *  barra de navegación (no tiene rutas propias aquí todavía). */
function RequireAppAccess({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  if (user.role !== "athlete" && user.role !== "coach") {
    return (
      <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 px-6 text-center">
        <h1 className="text-2xl font-bold">Esta app es para atletas y coaches</h1>
        <p className="text-muted">
          Tu cuenta es de administrador. Esas funciones viven en el panel de escritorio de
          NeuroLift.
        </p>
        <Button variant="secondary" onClick={() => void logout()}>
          Cerrar sesión
        </Button>
      </div>
    );
  }

  return <>{children}</>;
}

/** Dentro del shell, separa el árbol de rutas de atleta del de coach: si el rol no coincide,
 *  manda al home del rol correcto en vez de mostrar un 404 o la pantalla equivocada. */
function RoleGate({ role, children }: { role: Role; children: ReactNode }) {
  const user = useCurrentUser();
  if (user.role === role) return <>{children}</>;
  return <Navigate to={user.role === "coach" ? "/coach/atletas" : "/"} replace />;
}

function RedirectIfLogged({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

/** "/" no tiene un componente único: es el home de atleta, pero para un coach logueado debe
 *  mandar de una vez a su propio home en vez de mostrarle la pantalla de atleta un instante. */
function RootRoute() {
  const user = useCurrentUser();
  if (user.role === "coach") return <Navigate to="/coach/atletas" replace />;
  return <Today />;
}

export default function App() {
  return (
    <Routes>
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
            <RoleGate role="coach">
              <Groups />
            </RoleGate>
          }
        />
        <Route
          path="/coach/grupos/:groupId"
          element={
            <RoleGate role="coach">
              <GroupDetail />
            </RoleGate>
          }
        />
        <Route
          path="/coach/grupos/:groupId/programas/:programName/:startDate"
          element={
            <RoleGate role="coach">
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
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
