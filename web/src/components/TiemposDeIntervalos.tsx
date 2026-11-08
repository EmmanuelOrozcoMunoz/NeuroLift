import { formatSeconds } from "@/lib/dates";

function limitar(valor: string, maximo: number): number {
  const n = Number.parseInt(valor.replace(/\D/g, ""), 10);
  return Number.isNaN(n) ? 0 : Math.min(maximo, n);
}

/**
 * Los tiempos de un WOD por intervalos: una fila por intervalo (minutos y segundos) y el total abajo.
 * `valores` va en segundos, en orden. Gana el menor total.
 */
export function TiemposDeIntervalos({ valores, onChange }: { valores: number[]; onChange: (valores: number[]) => void }) {
  const total = valores.reduce((suma, v) => suma + v, 0);

  function cambiar(indice: number, segundos: number) {
    onChange(valores.map((v, i) => (i === indice ? segundos : v)));
  }

  return (
    <div>
      <ul className="space-y-2">
        {valores.map((segundos, i) => {
          const min = Math.floor(segundos / 60);
          const seg = segundos % 60;
          return (
            <li key={i} className="flex items-center gap-3 rounded-xl bg-surface-2 px-3 py-2">
              <span className="w-24 shrink-0 text-sm font-semibold">Intervalo {i + 1}</span>
              <div className="ml-auto flex items-center gap-1.5">
                <input
                  type="text"
                  inputMode="numeric"
                  aria-label={`Intervalo ${i + 1}, minutos`}
                  value={min}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => cambiar(i, limitar(e.target.value, 180) * 60 + seg)}
                  className="num h-11 w-14 rounded-lg border border-line bg-surface text-center text-base font-bold"
                />
                <span className="text-xs text-muted">min</span>
                <input
                  type="text"
                  inputMode="numeric"
                  aria-label={`Intervalo ${i + 1}, segundos`}
                  value={seg}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => cambiar(i, min * 60 + limitar(e.target.value, 59))}
                  className="num h-11 w-14 rounded-lg border border-line bg-surface text-center text-base font-bold"
                />
                <span className="text-xs text-muted">seg</span>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 text-center text-sm font-semibold text-muted">
        Total: <span className="num text-base text-fg">{formatSeconds(total)}</span>
      </p>
    </div>
  );
}
