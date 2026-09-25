import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "@/App";
import { UpdatePrompt } from "@/components/UpdatePrompt";
import { ApiError } from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import { initAccent } from "@/lib/brand";
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
initAccent();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
          <UpdatePrompt />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
