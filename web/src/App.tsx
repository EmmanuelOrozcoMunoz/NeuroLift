import { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { useAuth, useCurrentUser } from "@/lib/auth";
import { isStandalone } from "@/lib/pwa";
import type { Role, User } from "@/lib/types";
import Login from "@/routes/Login";
import Today from "@/routes/Today";

// Cada pantalla va en su propio paquete: un atleta no descarga el código del coach, del dueño ni del
// admin, y la app abre más rápido. Login y Today (el home del atleta) se quedan en el paquete principal
// porque son lo primero que se ve. La calculadora de Fit Level es la pantalla más pesada.
// Hay un <Suspense> en main.tsx (pantallas sueltas) y otro en AppShell (el menú se queda mientras carga).
const FitLevel = lazy(() => import("@/routes/FitLevel"));
const AdminBoxes = lazy(() => import("@/routes/admin/Boxes"));
const AdminLogs = lazy(() => import("@/routes/admin/Logs"));
const AdminOverview = lazy(() => import("@/routes/admin/Overview"));
const AdminUsers = lazy(() => import("@/routes/admin/Users"));
const AthleteDetail = lazy(() => import("@/routes/coach/AthleteDetail"));
const BoxDashboard = lazy(() => import("@/routes/box/BoxDashboard"));
const BoxHome = lazy(() => import("@/routes/box/BoxHome"));
const BoxTeam = lazy(() => import("@/routes/box/BoxTeam"));
const Athletes = lazy(() => import("@/routes/coach/Athletes"));
const Classes = lazy(() => import("@/routes/Classes"));
const GroupDetail = lazy(() => import("@/routes/coach/GroupDetail"));
const GroupProgramDetail = lazy(() => import("@/routes/coach/GroupProgramDetail"));
const Groups = lazy(() => import("@/routes/coach/Groups"));
const ForgotPassword = lazy(() => import("@/routes/ForgotPassword"));
const Landing = lazy(() => import("@/routes/Landing"));
const CoachMesocycleEditor = lazy(() => import("@/routes/coach/MesocycleEditor"));
const CoachPlanEditor = lazy(() => import("@/routes/coach/PlanEditor"));
const CoachPlans = lazy(() => import("@/routes/coach/Plans"));
const CoachTrainings = lazy(() => import("@/routes/coach/Trainings"));
const CoachProfile = lazy(() => import("@/routes/coach/Profile"));
const CoachSessionEditor = lazy(() => import("@/routes/coach/SessionEditor"));
const MesocycleDetail = lazy(() => import("@/routes/MesocycleDetail"));
const Mesocycles = lazy(() => import("@/routes/Mesocycles"));
const MyPersonalSessionEditor = lazy(() => import("@/routes/MyPersonalSessionEditor"));
const PlanDetail = lazy(() => import("@/routes/PlanDetail"));
const Plans = lazy(() => import("@/routes/Plans"));
const Profile = lazy(() => import("@/routes/Profile"));
const Ranking = lazy(() => import("@/routes/Ranking"));
const Register = lazy(() => import("@/routes/Register"));
const ResetPassword = lazy(() => import("@/routes/ResetPassword"));
const RegisterBox = lazy(() => import("@/routes/RegisterBox"));
const RegisterCoach = lazy(() => import("@/routes/RegisterCoach"));
const SessionDetail = lazy(() => import("@/routes/SessionDetail"));

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
/** "/box": el tablero para el dueño de un box activo; para la cuenta de un coach independiente
 *  (o un box todavía sin aprobar) es directamente la configuración de la cuenta. */
function BoxRoot() {
  const user = useCurrentUser();
  if (user.box?.kind === "box" && user.box.status === "active") return <BoxDashboard />;
  return <BoxHome />;
}

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
        path="/recuperar"
        element={
          <RedirectIfLogged>
            <ForgotPassword />
          </RedirectIfLogged>
        }
      />
      <Route path="/restablecer" element={<ResetPassword />} />
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
          path="/ranking"
          element={
            <RoleGate role="athlete">
              <Ranking />
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
        {/* "Actividad" se repartió: cada atleta muestra la suya en Atletas, y el ranking de un WOD vive en cada entreno */}
        <Route path="/coach/actividad" element={<Navigate to="/coach/atletas" replace />} />
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
          path="/coach/entrenos"
          element={
            <RoleGate role={COACH_ROLES}>
              <CoachTrainings />
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

        {/* ------------------------------------------------ clases y programación */}
        <Route
          path="/clases"
          element={
            <RoleGate role={COACH_ROLES}>
              <Classes />
            </RoleGate>
          }
        />
        {/* "Programar" se unió a Entrenos: es el único lugar para programar */}
        <Route path="/programacion" element={<Navigate to="/coach/entrenos" replace />} />

        {/* ------------------------------------------------------ dueño del box */}
        <Route
          path="/box"
          element={
            <RoleGate role="owner" allowInactiveBox>
              <BoxRoot />
            </RoleGate>
          }
        />
        <Route
          path="/box/ajustes"
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
