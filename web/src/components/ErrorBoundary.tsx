import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

import { reportError } from "@/lib/monitoring";

interface Props {
  children: ReactNode;
}

interface State {
  fallo: boolean;
}

/**
 * Atrapa los errores que ocurren al dibujar la app. Sin esto, React desmonta todo y el usuario se
 * queda con la pantalla en blanco; con esto ve un aviso y un botón para volver a cargar.
 * Los errores de las peticiones (401, 500...) NO pasan por aquí: los maneja cada pantalla.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { fallo: false };

  static getDerivedStateFromError(): State {
    return { fallo: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    reportError(error, { componentStack: info.componentStack });
  }

  render() {
    if (!this.state.fallo) return this.props.children;
    return (
      <div role="alert" className="mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10 text-center">
        <p className="text-sm font-semibold tracking-[0.2em] text-brand uppercase">NeuroLift</p>
        <h1 className="mt-2 text-2xl font-bold">Algo salió mal</h1>
        <p className="mt-2 text-sm text-muted">
          Ya tenemos el aviso. Vuelve a cargar la app; lo que tenías guardado sigue ahí.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-6 min-h-touch rounded-xl bg-brand px-6 font-semibold text-on-brand active:opacity-80"
        >
          Volver a cargar
        </button>
      </div>
    );
  }
}
