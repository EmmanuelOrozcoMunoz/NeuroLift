/** Explicación de cómo se calcula el Fit Level — la misma info para el panel del atleta y el
 *  del coach, para que no queden dos textos que se puedan desincronizar. Refleja exactamente
 *  la metodología de backend/fitness_scoring.py: si esa lógica cambia, este texto también. */
export function FitLevelCriteria() {
  return (
    <details className="mb-4 rounded-2xl border border-line bg-surface p-4 text-sm">
      <summary className="cursor-pointer font-semibold text-fg">¿Cómo se calcula el Fit Level?</summary>
      <div className="mt-3 space-y-3 text-muted">
        <p>
          Cada marca se puntúa en una escala de <strong className="text-fg">1 a 4</strong>:{" "}
          <strong className="text-fg">Principiante</strong>,{" "}
          <strong className="text-fg">Intermedio</strong>, <strong className="text-fg">Avanzado</strong>,{" "}
          <strong className="text-fg">Elite</strong> — comparando el desempeño contra tablas de
          referencia distintas para hombres y mujeres.
        </p>
        <ul className="list-disc space-y-1.5 pl-4">
          <li>
            <strong className="text-fg">🏋️ Halterofilia</strong> — se mide como razón{" "}
            <em>peso levantado / peso corporal</em>, no el kilaje absoluto: así un atleta liviano
            y uno pesado se comparan de forma justa.
          </li>
          <li>
            <strong className="text-fg">🤸 Gimnasia</strong> — repeticiones máximas absolutas
            (dominadas, push-ups, muscle-ups, HSPU).
          </li>
          <li>
            <strong className="text-fg">🔥 Metcon</strong> — tiempo en benchmarks clásicos (Fran,
            Grace, 2000m remo): menor tiempo es mejor. Cindy es la excepción — se puntúa por
            repeticiones totales en el AMRAP de 20 min.
          </li>
        </ul>
        <p>
          El nivel de cada categoría es el promedio de sus marcas registradas; el nivel general es
          el promedio de las categorías que tengan al menos una marca. Después de los{" "}
          <strong className="text-fg">35 años</strong> los estándares se relajan progresivamente
          (igual que las tablas de "masters" de halterofilia/powerlifting), y si falta el sexo del
          atleta se usa un promedio neutro entre ambas tablas mientras tanto.
        </p>
        <p className="text-xs italic">
          Son tablas propias, aproximadas — una referencia orientativa, no una medición
          competitiva oficial.
        </p>
      </div>
    </details>
  );
}
