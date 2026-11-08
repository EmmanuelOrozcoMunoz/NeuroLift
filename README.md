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
- **Arranque y esquema.** La creación de buckets corre en el `lifespan`, no al importar. La API **no crea tablas**: el esquema nace y cambia solo con Alembic (`0001_baseline` crea todo; `0002_knowledge_base` crea la tabla del RAG si hay pgvector). Correr `alembic upgrade head` en cada despliegue, antes de arrancar. CI lo corre desde cero y además `alembic check`, que falla si un modelo cambia sin su migración.
- **Planes plantilla y asignación a grupos.** Un plan (`is_template`) es una plantilla del coach: la crea a mano o con IA (`POST /ai/generate-plan-template/`, una sola generación sin atleta, con las cargas en % de 1RM) y la reutiliza. `POST /groups/{id}/assign-plan` la copia a cada miembro con fechas reales y los kg calculados con las marcas de cada atleta (`services/plans.py:asignar_plan_a_grupo`), sin llamar a la IA; asignarla otra vez en la misma fecha solo llega a quienes aún no la tenían. Quien no tenga una marca queda con su carga en % y se le avisa al coach.
- **WOD generado con IA.** El trabajo metabólico del día se devuelve en el campo `wod` de la sesión (formato, tiempo límite, descripción), no como ejercicios sueltos: `services/ai_salida.py:wod_limpio` lo valida (los 9 formatos que sabe puntuar y cronometrar la app) y `services/ai_mesocycles.py` lo guarda en la plantilla de WOD (`wod_format`, `wod_time_cap_seconds`, `wod_notes`), de donde el atleta obtiene el temporizador configurado. Un WOD inválido se descarta sin romper la generación.
- **Generación con IA: todos los componentes de una sesión, validados.** La IA devuelve lo mismo que arma un coach a mano: calentamiento en texto (`warmup_notes`), orden de bloques (`block_order`), nota por ejercicio (`coach_note`), series una por una (rampas, `series`) y WOD. Se le pide con un **esquema formal** de Gemini (`responseSchema`, `ai_agent.py:esquema_mesociclo`); si la API lo rechaza (400) la llamada se repite sin esquema. Nada de lo que devuelve se guarda sin pasar por `services/ai_salida.py` (sin base ni red, probado a fondo): tipos y rangos, bloques, textos y nombres de levantamientos canónicos (un solo "Back Squat" en el catálogo, no tres). Reglas que importan:
  - **Nunca un kg inventado:** un kg fijo para un levantamiento de barra sin marca de 1RM se descarta (queda por RPE) y el coach recibe un aviso (`advertencias` en la respuesta). Con marca, el % se resuelve con la marca de hoy.
  - **Las fechas las decide el calendario del coach, no la IA:** cada sesión se empareja con una fecha pedida; una fecha inventada o repetida se reasigna a una libre.
  - **Una tanda fallida o incompleta se reintenta una vez y, si sigue mal, se rechaza toda la generación.** Antes `generate_mesocycle_chunk` devolvía `{"error": ...}` y esa tanda se guardaba como vacía: quedaba un mesociclo al que le faltaban semanas, sin avisar.
  - Cada llamada registra en el log los **tokens** que gastó, y la respuesta trae el total (`uso`).
- **Borrador: la IA no le llega directo al atleta.** Un mesociclo generado con IA para un atleta nace con `Mesocycle.is_draft = true`: el atleta no lo ve (ni en su lista ni por id) ni puede registrar en él (`ocultar_borrador_al_atleta` en `core/security.py`, respuesta 404). Su coach lo ve marcado como *Borrador*, lo edita y lo publica con `POST /mesocycles/{id}/publish` (botón en la vista del mesociclo). Migración `0005`, aditiva (todo lo existente sigue publicado). La generación grupal por ahora sigue publicándose directo y las plantillas/planes no usan borrador.
- **Importar un plan desde PDF, Word o Excel.** El coach sube un archivo en *Mis planes → Importar* y ve cómo quedaría **antes de crear nada** (`POST /plan-import/preview`, sin guardar); al confirmar (`POST /plan-import/confirm`) se crea la plantilla **en borrador**, que se ajusta en el editor de planes y se asigna o publica como cualquier otra. `services/importar_plan.py` saca el texto del archivo (`pypdf`, `python-docx`, `openpyxl`: sin macros ni fórmulas; tipo por el contenido y no por la extensión; máx. 5 MB, 80 páginas, 80 000 caracteres; zips con límite de tamaño descomprimido; sin OCR: un PDF escaneado se rechaza con un mensaje claro) y `ai_agent.parse_training_document` lo transcribe con un esquema formal de Gemini (semanas, días, calentamiento, orden de bloques, WOD, notas, rampas). Reglas: **se transcribe, no se inventa**; los kg que escribió el coach se respetan aunque no haya marca (a diferencia de la generación con IA); el texto del archivo se trata como dato no confiable (delimitado y sin poder cerrar su etiqueta); al confirmar el servidor **limpia otra vez** el documento con `ai_salida` en vez de fiarse del cliente. Los días sin fecha en el documento se reparten (3 sesiones → lun/mié/vie). Cuesta lo de una llamada a Gemini por vista previa (límite de 10 por hora y usuario).
- **Programar cada bloque como un bloc de notas.** El coach puede escribir cada bloque de un día (calentamiento, fuerza, weightlifting, skills, WOD, accesorios, principal) como texto libre, sin estructurarlo en ejercicios y series. El calentamiento y el WOD siguen usando `warmup_notes` y `wod_notes` (el WOD conserva su formato, temporizador y tabla de posiciones); los demás viven en `Session.block_notes` (JSON `{bloque: texto}`, migración `0006`, aditiva; ver `services/block_notes.py`). Convive con los ejercicios estructurados del mismo bloque (el atleta ve el texto y debajo las series). Se edita en la sesión (`PUT /sessions/{id}/meta`), en un día de plan (`PUT /plans/{id}/sessions/{id}/meta`, y se copia al asignarlo) y para todo un grupo de una vez (`POST /groups/{id}/sessions/bulk-set-block-notes`, que también admite el calentamiento). Los valores del JSON no pasan por la limpieza automática de los esquemas, por eso `block_notes.py` los sanea uno por uno. Una sesión que solo tiene texto se termina con el mismo botón "Terminar entrenamiento".
- **Programar un día para el grupo desde el calendario.** En el detalle de un grupo hay un calendario con los días que tienen algo programado (de cualquier programa). Tocar un día abre una hoja: si ya está programado, enlaza a su editor; si no, "Programar este día" (`POST /groups/{id}/days`) crea una sesión vacía para **cada miembro** en el programa **"Programación diaria"** del grupo, sin armar un mesociclo, y abre ese día en el editor de grupo (texto por bloque, ejercicios y WOD para todos a la vez). Es un programa de grupo más (`services/groups.py:programar_dia_del_grupo`): idempotente (pedir un día que ya existe no duplica), la fecha de inicio del programa no se mueve al programar un día anterior (junto con el nombre identifica al programa) y los atletas que se unen después reciben los días ya programados. **Lo mismo para un atleta suelto:** el perfil de un atleta con coach personal (y fuera de un grupo) tiene su propio calendario; "Programar este día" (`POST /users/{id}/days`) crea la sesión vacía en el programa individual "Programación diaria" del atleta y abre el editor de sesión de siempre. También es idempotente; aquí la fecha de inicio sí se adelanta si se programa un día anterior, porque no hay una clave de programa que cuidar.
- **Imágenes: JPG, PNG, WEBP y HEIC.** `avatars.py` valida el contenido real del archivo (nunca la extensión), máx. 5 MB y 50 millones de píxeles (se rechaza por resolución antes de decodificar), reconstruye la imagen píxel por píxel (sin EXIF, GPS ni contenido escondido) y aplica antes la orientación del EXIF para que una foto de celular no quede de lado. Las fotos HEIC/HEIF del iPhone se leen con `pillow-heif` y **se guardan como JPG**, así ningún navegador necesita entender HEIC. GIF, SVG, BMP, TIFF y AVIF siguen sin admitirse. El front (`lib/images.ts`) reconoce un `.heic` también por su extensión, porque Windows lo manda sin tipo MIME.
- **Programación de grupo compacta.** En el editor de un día del grupo, los botones de añadir (bloques de texto, calentamiento, WOD y "+ Ejercicio") van en una sola fila; el formulario de ejercicio por ejercicio viene plegado y se recuerda en el dispositivo si el coach lo abre. Los bloques se ordenan para todo el grupo de una vez (`POST /groups/{id}/sessions/bulk-set-block-order`, que rechaza un bloque inexistente sin cambiar nada).
- **Menú del coach: cada cosa en un solo lugar.** La barra queda en **Atletas · Entrenos · Clases · Perfil** (Cuenta en lugar de Clases para el coach independiente; el dueño tiene Inicio y Box), sin "Programar" ni "Actividad".
  - **Entrenos** (`/coach/entrenos`) es el único lugar para programar y tiene tres vistas: **Lista**, **Calendario** y **Planes** (`/coach/planes`, las plantillas con las que se programa). Muestra todo lo programado para los grupos y los atletas personalizados (un día de grupo es **un** entreno; filtro `?grupo=` / `?atleta=`). **"+ Nuevo"** (o tocar un día) pregunta **qué** (un día, un mesociclo o un plan ya hecho) y **para quién** (un grupo o un atleta): el día se crea y se abre su editor; el mesociclo y el plan siguen en sus hojas de siempre. Por eso las pantallas de un grupo o de un atleta ya no traen botones de crear ni de asignar, solo un enlace a Entrenos filtrado. Backend: `GET /coach/trainings?date_from=&date_to=` (`services/entrenos.py`, máx. 400 días; sin plantillas, clases del box, registro propio ni sesiones adaptadas).
  - **Ranking por entreno.** Tocar un entreno que alguien ya terminó abre sus **resultados** (`GET /coach/trainings/{session_id}/results`): con un WOD con formato es el **ranking** por su resultado (mejor primero, 🥇🥈🥉, con el formato y el time cap); sin WOD, quién lo terminó y quién falta, sin posiciones (en una sesión de fuerza nadie "gana" por terminar antes). Un entreno sin terminar se abre directo para editarlo.
  - **Atletas** tiene tres pestañas: la lista (con cuántos entrenos completó cada uno esta semana y su último WOD), **Grupos** y **Ranking** del box (marcas y WODs). Ahí vive lo que antes era la pantalla "Actividad"; `/programacion` y `/coach/actividad` redirigen a Entrenos y a Atletas.
  - **El ranking del box** (`routes/Ranking.tsx`, lo comparten el atleta y el coach) tiene **una sola fila de opciones** (Snatch · Clean & Jerk · WODs); el **sexo** y, para el coach, el **grupo** viven en una hoja de filtros (la píldora "Filtros" muestra el resumen cuando hay alguno activo). Los **tres primeros van en un podio** (2.º · 1.º · 3.º, con avatar, medalla y resultado) y el resto en lista; en los WODs se muestra solo el resultado (el formato ya está en el título). Solo cuentan los WODs que el atleta anota en sus entrenos propios.
- **Evaluar la IA.** `services/ai_evaluacion.py` revisa lo que devuelve la IA (antes de limpiarlo) con reglas verificables: fechas, bloques, cargas sin marca, porcentajes, progresión entre semanas, enfoque pedido por día, y cuántos componentes de la sesión usó. Con la IA real y a mano (**gasta tokens**, necesita `GEMINI_API_KEY`): `python -m backend.evals.run_ia` (todos los casos), `--caso crossfit_sin_marcas`, o `--archivo respuesta.json --fechas ... --marcas "Back Squat=100"` para evaluar un JSON guardado sin gastar nada. Se corre antes y después de cambiar un prompt: sin números, "mejorar" el prompt es una opinión.
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
| `FRONTEND_URL` | URL pública del front, para los enlaces de los correos (por defecto, el primer `CORS_ORIGINS`) |
| `EMAIL_API_KEY`, `EMAIL_FROM` | Envío de correos (recuperar contraseña) con [Resend](https://resend.com). Sin la clave no se envía nada; en desarrollo el enlace sale en el log |
| `SENTRY_DSN` | (opcional) Errores 500 del backend a Sentry. El front usa `VITE_SENTRY_DSN` |
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

**Migraciones:** cambia `models.py` y corre `alembic revision --autogenerate -m "..."`; revisa el archivo generado y luego `alembic upgrade head`. Mantén cada migración aditiva cuando sea posible (las migraciones corren antes de mergear la promoción, con el código anterior todavía arriba). `alembic check` debe quedar limpio.

**Un ambiente que ya tenía el esquema** (de cuando lo creaba `create_all`: Dev y QA) no corre `0001`. Se verifica y se marca una sola vez:

```bash
alembic check          # debe decir "No new upgrade operations detected"
alembic stamp 0002     # o 0001 si esa base no tiene la tabla knowledge_base
```

---

## 4. Deuda conocida

- El limitador de peticiones guarda su cuenta en memoria: con más de una instancia habrá que moverlo a Redis.
- Funciones largas que aún conviene partir: `ai_agent.generate_mesocycle_chunk`, `sessions.adapt_session_to_available_time`, `boxes.get_owner_dashboard`.
