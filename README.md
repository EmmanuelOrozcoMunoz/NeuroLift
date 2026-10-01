# NeuroLift

Plataforma para que **boxes de CrossFit, coaches independientes y atletas** programen, sigan y registren entrenamientos. Es una PWA (se instala en el celular) con una API propia, y usa IA (Gemini) para ayudar a programar.

- **Coaches y boxes** programan mesociclos, planes y clases (las clases son solo para los entrenadores), y ven la actividad de sus atletas.
- **Atletas** ven lo que les toca hoy, registran series y marcas, y siguen su progreso.
- **Cada cliente** (un box o un coach) es una cuenta aislada, con su propio código de invitación, logo y color de acento.

> Estado: en producción de pruebas en **Dev** y **QA**. **PRD todavía no está configurado.**

---

## 1. Modelo de negocio (cómo funciona hoy)

### Quién paga y quién es el cliente
La unidad que paga es la **cuenta** (tabla `boxes`). Hay tres tipos:

| Tipo de cuenta (`kind`) | Quién es | Paga | Cómo se crea |
|---|---|---|---|
| `box` | Un gimnasio con dueño, profesores y atletas | Sí | El dueño se registra (`/boxes/register`); **queda pendiente hasta que un admin de la plataforma lo aprueba** |
| `coach` | Programar para **sus** atletas y grupos (los que él registró o tiene en grupos); crear planes; ver las clases del box y programar las que dicta; ver el ranking del box |
| `athlete` | Ver y registrar sus entrenamientos, marcas y actividad; adquirir planes; anotar su entreno del día (por ejemplo, lo que hizo en clase); ver el ranking de su box |

Un coach independiente y un box **pagan lo mismo** y por lo mismo: cuántos atletas tienen.

### Precios y suscripción
Los precios y límites viven en un solo lugar: `backend/core/billing.py` (el frontend los lee de `GET /boxes/pricing`).

| Plan | Atletas | Precio mensual (COP) |
|---|---|---|
| Básico | hasta 10 | 79.000 |
| Pro | hasta 30 | 149.000 |
| Ilimitado | 30 o más | 299.000 |

- **Prueba gratis de 14 días.** Empieza cuando el admin aprueba el box, o al registrarse un coach independiente.
- **Cobro manual por ahora.** Cuando un cliente paga, el admin de la plataforma registra el pago desde su panel (`POST /admin/boxes/{id}/payment`); eso extiende `paid_until` por 30 días por mes pagado. Un pago vigente manda sobre la prueba.
- **Qué se bloquea al vencer o al llegar al límite:** solo **agregar atletas nuevos** (por código o desde el panel del coach). Los atletas que ya están **nunca se bloquean**.
- Cuentan como atletas los usuarios con rol atleta de esa cuenta; el dueño y los coaches no cuentan.
- Los atletas con cuenta personal (`athlete`) no tienen límite ni cobro.

### Roles

| Rol | Qué puede hacer |
|---|---|
| `athlete` | Ver y registrar sus entrenamientos, marcas y actividad; adquirir planes; registrar clases del box |
| `coach` | Programar para **sus** atletas y grupos (los que él registró o tiene en grupos); crear planes; programar las clases donde es profesor |
| `owner` | Todo lo de un coach, sobre **todo su box**; crea clases y asigna profesores; gestiona coaches, perfil del box y ve el tablero del dueño |
| `admin` | Plataforma: aprobar o suspender boxes, registrar pagos, cambiar planes, ver auditoría. No gestiona el día a día de un box |

El dueño también hace de coach (es un coach con más alcance). Un box pendiente o suspendido bloquea a sus miembros; el dueño puede entrar para ver el estado de su solicitud.

### Qué recibe cada atleta

- **Atleta con coach personal** (lo registró un coach, o se registró con el código de un coach independiente): entrena con **mesociclos** que le programa su coach, y puede además adquirir planes y crear sesiones propias.
- **Atleta de un box sin coach personal:** anota su entreno por su cuenta (lo que hizo en clase o en casa). **Las clases del box no las ve**: son solo para los entrenadores. Los mesociclos son exclusivos de quienes tienen coach personal.
- **Atleta solo:** cuenta gratuita, con sus propias sesiones y los planes públicos. Puede **unirse después** a un box o a un coach con su código: conserva sus datos y su cuenta personal se elimina.

### Clases del box (solo entrenadores)
El **dueño** crea cada clase (nombre, días, hora, duración) y le asigna un **profesor**. El profesor (o el dueño) programa el contenido de la clase, ya sea como un bloque de varias semanas o día por día, con el mismo editor de sesiones de siempre. Todos los entrenadores del box ven el horario y el contenido; solo el profesor de la clase y el dueño lo editan.

**Los atletas no ven las clases**: la programación es confidencial del box. Si un atleta quiere registrar su entreno de la clase, lo anota a mano como una sesión propia («Anota tu entreno» en Hoy, o «+ Entreno» en Entrenos). El servidor lo hace cumplir: el horario, la lista de clases y la programación de una clase responden 403 a cualquier atleta.

### Ranking del box
Los atletas de un box (o de un coach independiente) tienen un **ranking entre ellos**, en la pestaña «Ranking». Los **entrenadores** de esa cuenta lo ven también, en la pestaña «Ranking» de **Actividad**.
- **Marcas (RM):** solo de los **levantamientos principales: Snatch y Clean & Jerk** (los demás no tienen ranking). La mejor marca de cada atleta, de mayor a menor. Los nombres se unifican («Clean & Jerk» y «clean and jerk» son el mismo levantamiento).
- **WODs:** por WOD y formato (Fran por tiempo, Cindy AMRAP…), el mejor intento de cada atleta. En por tiempo gana el menor; en AMRAP, el mayor.
- Se puede filtrar por sexo, y cada fila muestra si compite Rx o Scaled. Los empates comparten posición.
- **Privacidad:** cada atleta decide si aparece («¿Aparecer en el ranking de tu box?» en su perfil; por defecto sí). Quien lo apaga no sale en ninguna tabla, tampoco para los entrenadores. Nadie ve el ranking de otro box, y un atleta solo (sin box ni coach) no tiene ranking.
- **Confidencialidad:** en los WODs solo entran los que el atleta **anota a mano**; nunca los que le programa su coach ni los registros antiguos de clases, porque el nombre de un WOD suele traer su contenido.

### Tienda de planes
Un coach puede armar un **plan** (una plantilla de varias semanas con cargas en % de 1RM) y publicarlo con visibilidad `box` (solo atletas de su box) o `public` (toda la plataforma). Al **adquirirlo**, el atleta recibe una copia con fechas reales y los pesos calculados con sus propias marcas.
> Los planes tienen un campo de precio, pero **hoy adquirir un plan no cobra**: no hay pasarela de pagos.

### Personalización por cliente
Cada cuenta tiene logo, dirección, ciudad y un **color de acento** propio que recolorea la app para sus miembros. Los discos de las pesas usan siempre los colores oficiales IWF, nunca el acento.

### IA
Gemini genera sesiones y mesociclos completos (para un atleta o para un grupo, en paralelo), usando el peso corporal, las marcas del atleta y una base de conocimiento; también adapta una sesión al tiempo disponible. Las cargas que devuelve la IA se guardan como % y se resuelven con las marcas actuales del atleta, así que se mantienen al día si él mejora su 1RM. Hay límites por hora para cuidar el costo.

### Lo que todavía falta
- Inicio de sesión con Google y Apple.
- **Pasarela de pagos** (hoy el cobro es manual).
- Configurar **PRD**.

---

## 2. Arquitectura

**Monolito modular** con el frontend desacoplado: una sola API FastAPI, una sola base de datos Postgres y una PWA en React. No hay microservicios; el dominio está muy entrelazado (una serie toca sesiones, planes, clases y grupos) y separarlo por red solo traería transacciones distribuidas.

```mermaid
flowchart LR
    PWA["PWA (React 19 + Vite)<br/>Vercel"] -- "HTTPS + JWT" --> API["API FastAPI<br/>routers → services → core/modelos"]
    API --> DB[("Postgres<br/>Supabase")]
    API --> ST[("Supabase Storage<br/>avatares, portadas, logos")]
    API --> AI["Gemini<br/>generación de rutinas"]
```

### Backend (`backend/`)

La dependencia va **en un solo sentido**: `routers → services → core / models`. Ningún servicio ni router importa de otro router.

| Carpeta / archivo | Responsabilidad |
|---|---|
| `routers/` | La capa HTTP: valida la petición, comprueba permisos, llama a un servicio, hace `commit` y arma la respuesta. Un archivo por dominio (`auth`, `boxes`, `classes`, `groups`, `plans`, `mesocycles`, `sessions`, `sets`, `users`, `fitness`, `ranking`, `ai`, `admin`) |
| `services/` | Las reglas de negocio, **sin HTTP ni commit**: `classes` (horario de los entrenadores), `plans` (adquirir), `ranking` (marcas y WODs del box), `groups` (edición masiva, miembros nuevos), `ai_mesocycles` (generación con IA en pasos pequeños), `sets` (`clonar_set`), `prs` (marcas y % de 1RM), `exercises`, `group_access`, `boxes` |
| `core/` | `security` (JWT, roles, aislamiento entre clientes), `billing` (planes y suscripción), `errors` (excepciones de dominio), `config`, `invite`, `logging` (auditoría) |
| `models.py` · `schemas/` | Modelos SQLAlchemy (11 tablas) · esquemas Pydantic de entrada y salida (con saneamiento de texto) |
| `storage.py` · `avatars.py` · `ai_agent.py` | Supabase Storage, validación de imágenes, llamadas a Gemini |
| `migrations/` | Alembic |

**Ideas que conviene conocer**

- **Aislamiento entre clientes.** Todo cuelga de una cuenta (`boxes`). "Mis atletas" tiene una definición única (`_coach_athlete_ids` en `core/security.py`): el dueño ve a todo su box; un coach, a los que registró más los miembros de sus grupos; y nunca se cruza la frontera entre cuentas. Un recurso de otra cuenta responde igual que uno inexistente.
- **Errores de negocio.** Las reglas lanzan excepciones de dominio (`Prohibido`, `NoEncontrado`, `NoAutenticado`, `SolicitudInvalida`…) de `core/errors.py`, y **un solo manejador** en `main.py` las traduce a HTTP (mismo código y mensaje), registrando los 401/403 en la auditoría. Solo los routers usan `HTTPException`.
- **Copiar series.** `services/sets.py::clonar_set` es el único lugar que copia una serie (a un miembro nuevo de un grupo, al adquirir un plan). Cada columna de `Set` está declarada como "se copia" o "es de cada copia", y una prueba falla si se agrega una columna sin decidir.
- **Cargas en % de 1RM.** Los planes, las clases y la IA prescriben en %; el kg se calcula por atleta con sus marcas. Los nombres de ejercicio se normalizan (tildes, mayúsculas, `&`/`y`, alias en español) para reconocer la misma marca aunque cambie el nombre.
- **Clases.** Una clase es un `Mesocycle` con `class_id` y sin atleta, visible solo para los entrenadores de ese box (`ensure_can_view_mesocycle`). Los registros antiguos de atletas (`is_class_log`) se conservan como historial hasta que se purguen con `backend/scripts/purgar_registros_de_clase.py`.
- **Arranque.** `create_all()` y la creación de buckets corren en el `lifespan`, no al importar. Como ninguna migración crea el esquema base, un ambiente nuevo todavía lo necesita; por eso una migración que crea una tabla debe tolerar que ya exista.
- **Planes plantilla y asignación a grupos.** Un plan (`is_template`) es una plantilla del coach: la crea a mano o con IA (`POST /ai/generate-plan-template/`, una sola generación sin atleta, con las cargas en % de 1RM) y la reutiliza. `POST /groups/{id}/assign-plan` la copia a cada miembro con fechas reales y los kg calculados con las marcas de cada atleta (`services/plans.py:asignar_plan_a_grupo`), sin llamar a la IA; asignarla otra vez en la misma fecha solo llega a quienes aún no la tenían. Quien no tenga una marca queda con su carga en % y se le avisa al coach.
- **WOD generado con IA.** El trabajo metabólico del día se devuelve en el campo `wod` de la sesión (formato, tiempo límite, descripción), no como ejercicios sueltos: `services/ai_mesocycles.py:wod_limpio` lo valida y lo guarda en la plantilla de WOD (`wod_format`, `wod_time_cap_seconds`, `wod_notes`), de donde el atleta obtiene el temporizador configurado. Un WOD inválido se descarta sin romper la generación.
- **Concurrencia.** Los endpoints son síncronos (40 hilos por proceso) y cada petición retiene una conexión de la base (30 por proceso). Con más peticiones en vuelo que conexiones, se bloqueaban entre sí y el servicio colapsaba (de ~100 a ~3 peticiones por segundo). `core/concurrency.py` limita cuántas se procesan a la vez por proceso: las demás esperan en cola y, si esperan más de 15 s, reciben un 503 con `Retry-After`. El límite va por dentro de CORS y no afecta a `/` (el health check). Con varios procesos (workers) el límite es **por proceso**, y las conexiones a la base se multiplican: hay que revisar el máximo de conexiones del plan de Supabase.
- **Seguridad.** JWT con revocación real (`token_version`), límites de peticiones por IP y usuario, cabeceras de seguridad, texto saneado en todos los esquemas y `/docs` apagado en producción.

### Frontend (`web/`)

React 19 · TypeScript · Vite 8 · Tailwind 4 (tokens en `@theme`, tema "Dark Energy") · React Router 7 · TanStack Query 5 · PWA con `vite-plugin-pwa` (instalable, con aviso de actualización) · landing pública en `/bienvenida`.

| Carpeta | Contenido |
|---|---|
| `src/routes/` | Pantallas por rol: atleta (Hoy, Entrenos, Planes), `coach/`, `box/` (dueño) y `admin/` |
| `src/components/` | Componentes compartidos: `AppShell` (navegación por rol), `ExerciseFormFields` (el formulario de ejercicio de sesión, plan y grupo), `SessionSetsEditor`, `ClassCard`, `ui` |
| `src/lib/` | Consultas (`queries`, `coachQueries`, `classQueries`), `api`, `brand` (color de acento), `units`, y `types/` (tipos por dominio, espejo de `backend/schemas/`) |

Diseño mobile-first: la pantalla "Hoy" es el centro para el atleta y el resto se organiza en navegación inferior por rol.

### Ambientes y flujo de trabajo

| Ambiente | Rama | Base de datos |
|---|---|---|
| Dev | `Dev` | Supabase `NeuroLift` |
| QA | `qa` | Supabase `NeuroLift-qa` |
| PRD | *(por definir; `main` hoy es el checkout anterior a la reescritura)* | *(sin configurar)* |

1. Cada cambio va en una rama que sale de `Dev` y se integra con un **PR a `Dev`**.
2. Se promueve con un **PR de `Dev` a `qa`**. Las migraciones se corren **antes** de mergear la promoción (son aditivas, así que el código anterior sigue funcionando).
3. El CI corre en cada PR hacia `Dev` y `qa`: importa el backend, corre las pruebas del backend (Postgres descartable) y las del frontend, y hace typecheck y build.

---

## 3. Desarrollo local

Requisitos: Python 3.11 y Node 20+.

**Variables de entorno** (`.env` en la raíz; no se sube al repo):

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Postgres |
| `JWT_SECRET_KEY` | Firma de tokens (obligatoria) |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | Storage de imágenes (obligatorias) |
| `GEMINI_API_KEY` | Generación con IA |
| `CORS_ORIGINS` | Orígenes permitidos del frontend |
| `ENVIRONMENT` | `production` apaga `/docs` |
| `MAX_CONCURRENT_REQUESTS` | (opcional, 20) Peticiones que procesa a la vez **cada proceso** de la API; las demás esperan en cola. 0 lo desactiva. Se recorta a las conexiones del pool (30) |
| `HTTP_QUEUE_TIMEOUT_SECONDS` | (opcional, 15) Cuánto espera una petición en cola antes de recibir un 503 |
| `DB_POOL_TIMEOUT` | (opcional, 10) Segundos que una petición espera una conexión libre a la base antes de fallar |
| `VITE_API_URL` | (en `web/`) URL de la API |

```bash
# API
python -m venv venv && venv/Scripts/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn backend.main:app --reload --port 8000
```

```bash
# Web
cd web && npm ci && npm run dev
```

**Pruebas**

```bash
# Backend: necesita un Postgres DESCARTABLE. Se niega a correr contra Supabase.
pip install -r requirements-dev.txt
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres pytest

# Frontend
cd web && npm test
```

**Migraciones:** `alembic revision -m "..."` y luego `alembic upgrade head`. Mantén cada migración tolerante a re-ejecución y aditiva cuando sea posible.

---

## 4. Deuda conocida

- Falta una **migración inicial** que cree el esquema base (hoy lo hace `create_all` al arrancar).
- El limitador de peticiones guarda su cuenta en memoria: con más de una instancia habrá que moverlo a Redis.
- Funciones largas que aún conviene partir: `ai_agent.generate_mesocycle_chunk`, `sessions.adapt_session_to_available_time`, `boxes.get_owner_dashboard`.
