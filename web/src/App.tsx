import { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { useAuth, useCurrentUser } from "@/lib/auth";
import { isStandalone } from "@/lib/pwa";
import type { Role, User } from "@/lib/types";
import AdminBoxes from "@/routes/admin/Boxes";
import AdminLogs from "@/routes/admin/Logs";
import AdminOverview from "@/routes/admin/Overview";
import AdminUsers from "@/routes/admin/Users";
import AthleteDetail from "@/routes/coach/AthleteDetail";
import BoxHome from "@/routes/box/BoxHome";
import BoxTeam from "@/routes/box/BoxTeam";
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
import RegisterBox from "@/routes/RegisterBox";
import RegisterCoach from "@/routes/RegisterCoach";
import SessionDetail from "@/routes/SessionDetail";
import Today from "@/routes/Today";

// La calculadora de Fit Level es la pantalla más pesada (14 campos + tablas de baremos) y
// la que menos se abre: va en su propio chunk.
const FitLevel = lazy(() => import("@/routes/FitLevel"));

// Coach y dueño del box comparten todas las pantallas de programación
const COACH_ROLES: Role[] = ["coach", "owner"];

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

function homeForRole(user: User): string {
  const { role } = user;
  // El coach independiente (dueño de una cuenta tipo "coach") trabaja como cualquier coach
  if (role === "coach" || (role === "owner" && user.box?.kind === "coach")) return "/coach/atletas";
  if (role === "owner") return "/box";
  if (role === "admin") return "/admin";
  return "/";
}

/** Dentro del shell, separa el árbol de rutas de atleta/coach/admin: si el rol no coincide
 *  con ninguno de los aceptados, manda al home del rol correcto en vez de mostrar un 404 o
 *  la pantalla equivocada. */
function RoleGate({
  role,
  allowInactiveBox = false,
  children,
}: {
  role: Role | Role[];
  /** El dueño con el box pendiente/suspendido solo puede entrar a las rutas que lo permitan
   *  (su panel y su perfil); el resto de pantallas de coach le responderían 403. */
  allowInactiveBox?: boolean;
  children: ReactNode;
}) {
  const user = useCurrentUser();
  const allowed = Array.isArray(role) ? role : [role];
  if (!allowed.includes(user.role)) return <Navigate to={homeForRole(user)} replace />;
  if (user.role === "owner" && user.box?.status !== "active" && !allowInactiveBox) {
    return <Navigate to="/box" replace />;
  }
  return <>{children}</>;
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
  if (user.role !== "athlete") return <Navigate to={homeForRole(user)} replace />;
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
        path="/registro-coach"
        element={
          <RedirectIfLogged>
            <RegisterCoach />
          </RedirectIfLogged>
        }
      />
      <Route
        path="/registrar-box"
        element={
          <RedirectIfLogged>
            <RegisterBox />
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
            <RoleGate role={COACH_ROLES}>
              <Athletes />
            </RoleGate>
          }
        />
        <Route
          path="/coach/actividad"
          element={
            <RoleGate role={COACH_ROLES}>
              <Leaderboard />
            </RoleGate>
          }
        />
        <Route
          path="/coach/atletas/:athleteId"
          element={
            <RoleGate role={COACH_ROLES}>
              <AthleteDetail />
            </RoleGate>
          }
        />
        <Route
          path="/coach/grupos"
          element={
            <RoleGate role={[...COACH_ROLES, "admin"]}>
              <Groups />
            </RoleGate>
          }
        />
        <Route
          path="/coach/grupos/:groupId"
          element={
            <RoleGate role={[...COACH_ROLES, "admin"]}>
              <GroupDetail />
            </RoleGate>
          }
        />
        <Route
          path="/coach/grupos/:groupId/programas/:programName/:startDate"
          element={
            <RoleGate role={[...COACH_ROLES, "admin"]}>
              <GroupProgramDetail />
            </RoleGate>
          }
        />
        <Route
          path="/coach/mesociclos/:mesocycleId"
          element={
            <RoleGate role={COACH_ROLES}>
              <CoachMesocycleEditor />
            </RoleGate>
          }
        />
        <Route
          path="/coach/mesociclos/:mesocycleId/sesion/:sessionId"
          element={
            <RoleGate role={COACH_ROLES}>
              <CoachSessionEditor />
            </RoleGate>
          }
        />
        <Route
          path="/coach/planes"
          element={
            <RoleGate role={COACH_ROLES}>
              <CoachPlans />
            </RoleGate>
          }
        />
        <Route
          path="/coach/planes/:planId"
          element={
            <RoleGate role={COACH_ROLES}>
              <CoachPlanEditor />
            </RoleGate>
          }
        />
        <Route
          path="/coach/perfil"
          element={
            <RoleGate role={COACH_ROLES} allowInactiveBox>
              <CoachProfile />
            </RoleGate>
          }
        />

        {/* ------------------------------------------------------ dueño del box */}
        <Route
          path="/box"
          element={
            <RoleGate role="owner" allowInactiveBox>
              <BoxHome />
            </RoleGate>
          }
        />
        <Route
          path="/box/equipo"
          element={
            <RoleGate role="owner">
              <BoxTeam />
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
          path="/admin/boxes"
          element={
            <RoleGate role="admin">
              <AdminBoxes />
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
