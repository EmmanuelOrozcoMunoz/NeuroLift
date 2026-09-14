# Graph Report - NeuroLift  (2026-09-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 834 nodes · 2437 edges · 70 communities (35 shown, 18 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 12 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `24a18234`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ui.tsx
- Leaderboard.tsx
- main.py
- Session
- package.json
- HTTPException
- types.ts
- schemas.py
- AppShell.tsx
- Today.tsx
- _build_smart_mesocycle
- SessionDetail.tsx
- wod.ts
- get
- ai_agent.py
- app.py
- apiFetch
- compilerOptions
- App.tsx
- upload_plan_cover
- BaseModel
- queries.ts
- GroupProgramDetail.tsx
- fitness_scoring.py
- PlanDetail.tsx
- read_and_validate_upload
- get_plan_cover
- ExerciseBlock
- migrate_uploads_to_storage.py
- CreateMesocycleSheet
- env.py
- clean_text
- AddMembersSheet
- DayEditor
- GroupDetail
- useRegisterAthlete
- useCreatePlan
- useSearchAthleteByEmail
- useUpdatePlan
- GroupSessionExerciseDelete
- AthleteActivityResponse
- GroupMesocycleProgram
- GroupSessionExerciseAdd
- PlanPreviewResponse
- PlanSessionPreview
- PlanSetCreate
- WodFormatUpdate
- SessionCompleteRequest
- RecentSessionExercise
- UserRoleUpdate
- WodDaySummary
- WodLeaderboardRow
- useGroupBulkAdd

## God Nodes (most connected - your core abstractions)
1. `Session` - 81 edges
2. `apiFetch()` - 58 edges
3. `SanitizedModel` - 33 edges
4. `cx()` - 28 edges
5. `react` - 28 edges
6. `ensure_owner_or_coach()` - 26 edges
7. `react-router-dom` - 24 edges
8. `Button()` - 22 edges
9. `PageHeader()` - 20 edges
10. `compilerOptions` - 20 edges

## Surprising Connections (you probably didn't know these)
- `AthleteDetail()` --indirect_call--> `formatKg()`  [INFERRED]
  web/src/routes/coach/AthleteDetail.tsx → web/src/lib/dates.ts
- `AuthState` --references--> `User`  [EXTRACTED]
  web/src/lib/auth.tsx → web/src/lib/types.ts
- `update_fitness_benchmarks()` --calls--> `FitnessBenchmark`  [EXTRACTED]
  backend/main.py → backend/models.py
- `_get_owned_group()` --references--> `Group`  [EXTRACTED]
  backend/main.py → backend/models.py
- `_build_manual_mesocycle()` --calls--> `Mesocycle`  [EXTRACTED]
  backend/main.py → backend/models.py

## Import Cycles
- None detected.

## Communities (70 total, 18 thin omitted)

### Community 0 - "ui.tsx"
Cohesion: 0.10
Nodes (36): react, FitLevel, ACCEPTED_TYPES, CoverThumbnail(), DISCIPLINAS, Badge(), Button(), ButtonProps (+28 more)

### Community 1 - "Leaderboard.tsx"
Cohesion: 0.08
Nodes (34): @tanstack/react-query, App(), ACCEPTED_TYPES, AvatarUploader(), CoverUploader(), handleFileChange(), ApiError, apiFetchBlob() (+26 more)

### Community 2 - "main.py"
Cohesion: 0.07
Nodes (42): add_security_headers(), _build_manual_mesocycle(), _client_ip(), create_access_token(), create_manual_mesocycle_for_group(), create_plan(), _format_wod_summary(), get_athlete_leaderboard() (+34 more)

### Community 3 - "Session"
Cohesion: 0.16
Nodes (38): add_exercise_to_group_session(), add_group_members(), add_set_to_plan_session(), delete_exercise_from_group_session(), delete_group(), delete_group_cover(), delete_my_avatar(), delete_plan() (+30 more)

### Community 4 - "package.json"
Cohesion: 0.06
Nodes (34): react-dom, tailwindcss, @tailwindcss/vite, @types/node, @types/react, @types/react-dom, typescript, vite (+26 more)

### Community 5 - "HTTPException"
Cohesion: 0.11
Nodes (35): adapt_session_to_available_time(), agregar_serie(), _build_fitness_level_response(), _clean_ai_block(), complete_session(), create_manual_mesocycle(), create_mesocycle(), create_session() (+27 more)

### Community 6 - "types.ts"
Cohesion: 0.10
Nodes (30): AIGenerateSmartGroupPayload, AIGenerateSmartPayload, BulkResponse, BulkResultRow, CreateGroupPayload, Exercise, FitCategory, GroupBulkAddPayload (+22 more)

### Community 7 - "schemas.py"
Cohesion: 0.11
Nodes (30): AIGenerateRequest, AIGenerateSmart, AIGenerateSmartGroup, FitnessBenchmarkUpdate, GroupCreate, GroupMemberAdd, GroupSessionExerciseUpdate, GroupSessionWodFormatUpdate (+22 more)

### Community 8 - "AppShell.tsx"
Cohesion: 0.19
Nodes (21): react-router-dom, ATHLETE_NAV, COACH_NAV, PageHeader(), IconBack(), IconCamera(), IconChevronRight(), IconDumbbell() (+13 more)

### Community 9 - "Today.tsx"
Cohesion: 0.19
Nodes (23): SectionTitle(), daysFromToday(), DIAS, DIAS_CORTOS, longDate(), MESES, parseApiDate(), shortWeekdayName() (+15 more)

### Community 10 - "_build_smart_mesocycle"
Cohesion: 0.11
Nodes (22): main(), acquire_plan(), _build_smart_mesocycle(), _clone_mesocycle_for_athlete(), create_group(), Genera con IA un mesociclo inteligente completo para UN atleta. Hace commit…, Convierte un % de 1RM a kg usando las marcas del atleta, redondeando a…, El atleta adquiere un plan publicado: se clona a un mesociclo propio con las… (+14 more)

### Community 11 - "SessionDetail.tsx"
Cohesion: 0.17
Nodes (19): IconCheck(), IconClock(), SessionCard(), SetRow(), formatKg(), relativeDay(), useAdaptSession(), useCompleteSession() (+11 more)

### Community 12 - "wod.ts"
Cohesion: 0.10
Nodes (21): WodFormatCard(), elegir(), guardar(), Fase, Modo, pitar(), resolverModo(), WodTimer() (+13 more)

### Community 13 - "get"
Cohesion: 0.08
Nodes (25): _coach_athlete_ids(), get_admin_overview(), get_athletes(), get_full_mesocycle(), get_plan_detail(), get_recent_activity(), get_users(), list_my_groups() (+17 more)

### Community 14 - "ai_agent.py"
Cohesion: 0.12
Nodes (16): adapt_session_to_time(), _generate_json_with_fallback(), generate_mesocycle_chunk(), generate_workout_session(), _post_to_gemini(), Busca en el PDF inyectado los párrafos más relevantes para el atleta., `literatura_cientifica` se calcula UNA sola vez por mesociclo…, Toma los ejercicios YA prescritos para una sesión y los adapta (menos series,… (+8 more)

### Community 15 - "app.py"
Cohesion: 0.15
Nodes (20): _check_revoked_session(), get_headers(), _patched_delete(), _patched_get(), _patched_post(), _patched_put(), Editor de 'grupo completo': igual que el editor individual (ver ejercicios…, Lista los mesociclos programados para un grupo y, para cada uno, una pestaña… (+12 more)

### Community 16 - "apiFetch"
Cohesion: 0.17
Nodes (18): apiFetch(), useAthletes(), useCreateGroup(), useDeletePlan(), useGroupBulkDelete(), useGroupBulkUpdate(), useGroups(), useMyPlans() (+10 more)

### Community 17 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+13 more)

### Community 18 - "App.tsx"
Cohesion: 0.16
Nodes (15): RedirectIfLogged(), RequireAppAccess(), RoleGate(), RootRoute(), AppShell(), useOnline(), useAuth(), useCurrentUser() (+7 more)

### Community 19 - "upload_plan_cover"
Cohesion: 0.15
Nodes (19): Decodifica la imagen y la reconstruye en un lienzo completamente nuevo,…, rerender_and_strip_metadata(), generate_and_save_smart_mesocycle_for_group(), _plan_summary(), UploadFile, Genera con IA el mismo mesociclo (contexto compartido + marcas propias de cada…, Edita nombre/descripción/disciplina/nivel/precio de un plan — funciona igual…, Sube (o reemplaza) la foto de perfil del usuario autenticado. Solo uno mismo… (+11 more)

### Community 20 - "BaseModel"
Cohesion: 0.15
Nodes (20): AdminOverview, Config, ExerciseResponse, FitnessLevelResponse, GroupMemberResponse, GroupMesocycleAthlete, GroupResponse, GroupSummaryResponse (+12 more)

### Community 21 - "queries.ts"
Cohesion: 0.12
Nodes (18): CompleteSessionVars, LogSetVars, queryKeys, useFitnessLevel(), useSaveBenchmarks(), FitnessLevel, MesocycleSummary, MessageResponse (+10 more)

### Community 22 - "GroupProgramDetail.tsx"
Cohesion: 0.20
Nodes (14): BlockSelect(), IconTrash(), SessionSetsEditor(), useGroupMesocycles(), shortDate(), groupByBlock(), TrainingSession, WOD_OTHER_SCORE_TYPES (+6 more)

### Community 23 - "fitness_scoring.py"
Cohesion: 0.22
Nodes (12): _age_multiplier(), _bounds_for(), compute_fitness_level(), Calculadora de 'Fit Level' para CrossFit: halterofilia, gimnasia y metcon.…, values: {metric_key: value} solo con las métricas que el atleta ya registró., bounds = [max_principiante, max_intermedio, max_avanzado] (ascendente)., bounds = [max_elite, max_avanzado, max_intermedio] (ascendente, en segundos)., Cuánto se 'relajan' los estándares por edad (1.0 = sin ajuste, edades <=35).… (+4 more)

### Community 24 - "PlanDetail.tsx"
Cohesion: 0.26
Nodes (10): BLOCK_KEYS, BLOCK_LABELS, BLOCK_OPTIONS, BlockKey, blockLabel(), formatPrice(), useAcquirePlan(), usePlanCatalog() (+2 more)

### Community 25 - "read_and_validate_upload"
Cohesion: 0.24
Nodes (8): AvatarRejected, HTTPException, UploadFile, Validación y saneo de imágenes subidas por el usuario (avatar, portada de…, Identifica el formato real por su firma binaria. Devuelve None si no coincide…, Lee el archivo del request respetando el límite de tamaño DESDE la lectura…, read_and_validate_upload(), _sniff_magic_number()

### Community 26 - "get_plan_cover"
Cohesion: 0.25
Nodes (8): get_plan_cover(), get_user_avatar(), Mismo criterio de visibilidad que GET /plans/{id}: el autor/admin ve la portada…, Cualquier usuario autenticado puede ver la foto de perfil de otro (no es…, Redirige a una URL firmada de corta duración de Supabase Storage — los buckets…, _redirect_to_image(), create_signed_url(), Pide una URL firmada de corta duración (el navegador la usa de inmediato, así…

### Community 27 - "ExerciseBlock"
Cohesion: 0.25
Nodes (5): AddExerciseForm(), ExerciseBlock(), useAddSet(), useDeleteSet(), useUpdateSet()

### Community 28 - "migrate_uploads_to_storage.py"
Cohesion: 0.29
Nodes (6): main(), Sube a Supabase Storage lo que haya quedado en backend/uploads/ (del…, ensure_buckets(), Crea los buckets privados si todavía no existen. Idempotente: seguro de llamar…, Como upload_object, pero con una key EXPLÍCITA en vez de generar una nueva —…, upload_object_as()

### Community 29 - "CreateMesocycleSheet"
Cohesion: 0.33
Nodes (7): CreateMesocycleSheet(), handleSubmit(), reset(), useCreateManualMesocycle(), useCreateManualMesocycleForGroup(), useGenerateAIMesocycle(), useGenerateAIMesocycleForGroup()

### Community 30 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 31 - "clean_text"
Cohesion: 0.40
Nodes (3): clean_text(), Sanea un texto libre antes de guardarlo: quita cualquier HTML/script (bleach,…, model_validator

### Community 33 - "DayEditor"
Cohesion: 0.50
Nodes (3): useAddPlanSet(), useDeletePlanSet(), DayEditor()

### Community 34 - "GroupDetail"
Cohesion: 0.50
Nodes (4): useDeleteGroup(), useGroupDetail(), useRemoveGroupMember(), GroupDetail()

### Community 35 - "useRegisterAthlete"
Cohesion: 0.67
Nodes (4): useRegisterAthlete(), RegisterAthleteSheet(), handleSubmit(), reset()

## Knowledge Gaps
- **92 isolated node(s):** `ButtonProps`, `ButtonVariant`, `FieldProps`, `TipoCarga`, `TimeValue` (+87 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 285 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `react` connect `ui.tsx` to `Leaderboard.tsx`, `package.json`, `AppShell.tsx`, `SessionDetail.tsx`, `wod.ts`, `apiFetch`, `App.tsx`, `GroupProgramDetail.tsx`, `PlanDetail.tsx`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `Session` connect `Session` to `main.py`, `HTTPException`, `_build_smart_mesocycle`, `get`, `upload_plan_cover`, `get_plan_cover`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `apiFetch()` connect `apiFetch` to `ui.tsx`, `Leaderboard.tsx`, `types.ts`, `Today.tsx`, `SessionDetail.tsx`, `wod.ts`, `queries.ts`, `GroupProgramDetail.tsx`, `PlanDetail.tsx`, `ExerciseBlock`, `CreateMesocycleSheet`, `AddMembersSheet`, `DayEditor`, `GroupDetail`, `useRegisterAthlete`, `useCreatePlan`, `useSearchAthleteByEmail`, `useUpdatePlan`, `useGroupBulkAdd`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **What connects `ButtonProps`, `ButtonVariant`, `FieldProps` to the rest of the system?**
  _92 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ui.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.09568627450980392 - nodes in this community are weakly interconnected._
- **Should `Leaderboard.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07536231884057971 - nodes in this community are weakly interconnected._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07188160676532769 - nodes in this community are weakly interconnected._