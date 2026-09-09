import { Suspense, lazy } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { Button, Spinner } from "@/components/ui";
import { useAuth } from "@/lib/auth";
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

/** Solo atletas: coach y admin siguen operando desde el panel de escritorio. */
function RequireAthlete({ children }: { children: ReactNode }) {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  if (user.role !== "athlete") {
    return (
      <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-4 px-6 text-center">
        <h1 className="text-2xl font-bold">Esta app es para atletas</h1>
        <p className="text-muted">
          Tu cuenta es de {user.role === "coach" ? "entrenador" : "administrador"}. Esas funciones
          viven en el panel de escritorio de NeuroLift.
        </p>
        <Button variant="secondary" onClick={() => void logout()}>
          Cerrar sesión
        </Button>
      </div>
    );
  }

  return <>{children}</>;
}

function RedirectIfLogged({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
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
          <RequireAthlete>
            <AppShell />
          </RequireAthlete>
        }
      >
        <Route path="/" element={<Today />} />
        <Route path="/entrenos" element={<Mesocycles />} />
        <Route path="/entrenos/:mesocycleId" element={<MesocycleDetail />} />
        <Route path="/entrenos/:mesocycleId/sesion/:sessionId" element={<SessionDetail />} />
        <Route path="/planes" element={<Plans />} />
        <Route path="/planes/:planId" element={<PlanDetail />} />
        <Route path="/perfil" element={<Profile />} />
        <Route
          path="/perfil/fit-level"
          element={
            <Suspense fallback={<FullScreenLoader />}>
              <FitLevel />
            </Suspense>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
