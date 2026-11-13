import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "@/App";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Spinner } from "@/components/ui";
import { UpdatePrompt } from "@/components/UpdatePrompt";
import { ApiError } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import { initAccent } from "@/lib/brand";
import { initMonitoring } from "@/lib/monitoring";
import { initTema } from "@/lib/theme";
// Efecto secundario: registra el listener de beforeinstallprompt lo antes posible
import "@/lib/pwa";
import "@/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // En el gimnasio la señal va y viene: se reintenta, pero nunca ante un error del
      // cliente (401/403/404 no se arreglan reintentando).
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
        return failureCount < 2;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: true,
    },
  },
});

// Antes de montar: el acento del box se aplica sin mostrar un instante el color por defecto
initTema(); // antes del acento: en claro, el acento de la cuenta se ajusta para leerse sobre blanco
initAccent();
initMonitoring();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            {/* Pantallas sueltas (login, registro...) que se cargan bajo demanda */}
            <Suspense
              fallback={
                <div className="flex min-h-dvh items-center justify-center">
                  <Spinner className="h-8 w-8 text-brand" />
                </div>
              }
            >
              <App />
            </Suspense>
            <UpdatePrompt />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
);
