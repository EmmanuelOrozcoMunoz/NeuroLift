# Graph Report - NeuroLift  (2026-09-25)

## Corpus Check
- 284 files · ~309,448 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 65 file(s) not represented in the graph (top: .csv 53, (none) 5, .example 2)

## Summary
- 3688 nodes · 6940 edges · 237 communities (172 shown, 34 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.87)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6e0d0716`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AppShell.tsx
- ui.tsx
- validate_accent
- routers/plans.py
- package.json
- BoxHome.tsx
- types.ts
- Session
- test_design_system_mode.py
- dates.ts
- models.py
- validate_data.py
- cip/core.py
- gray
- _build_smart_mesocycle
- slide_search_core.py
- FitLevel.tsx
- compilerOptions
- apiFetch
- routers/users.py
- Tailwind CSS Utility Reference
- Brand Guidelines v1.0
- GroupProgramDetail.tsx
- fitness_scoring.py
- Design
- avatars.py
- Canvas Design System
- Form & Input Components
- routers/boxes.py
- Tailwind CSS Responsive Design
- env.py
- App.tsx
- search_stack
- Typography Specifications
- TestTailwindConfigGenerator
- search
- Logo Usage Rules
- Component Specifications
- html-token-validator.py
- shadcn/ui Accessibility Patterns
- scripts/core.py
- logo/core.py
- What You Must Do When Invoked
- Asset Approval Checklist
- Logo AI Prompt Engineering
- design_system.py
- Color Palette Management
- CIP Deliverable Guide
- States and Variants
- UI Styling Skill
- test_data_contracts.py
- Workflow
- DesignSystemGenerator
- Design System
- Tailwind CSS Customization
- spacing
- TailwindConfigGenerator
- AvatarUploader.tsx
- schemas/__init__.py
- logging_http_exception_handler
- generate-slide.py
- wodFormatUsesTimeCap
- read_rows
- adapt_session_to_available_time
- Routing by Task Type
- shadcn/ui Theming & Customization
- Asset Organization Guide
- Primary Color Meanings
- Core Logo Types
- fetch-background.py
- color
- Brand Consistency Checklist
- CIP Mockup Prompt Engineering
- Color Semantics
- TestThresholdGate
- icon/generate.py
- BM25
- CatalogRefreshTest
- schemas/mesocycles.py
- _normalize
- Design Principles
- Design Principles
- fontSize
- TestShadcnInstaller
- CIP Design Reference
- Icon Design Reference
- Copywriting Formulas
- Copywriting Formulas
- detect_domain
- RegisterAthleteSheet
- Banner Design - Multi-Format Creative Banner System
- Messaging Framework
- Brand Voice Framework
- extract-colors.cjs
- validate-asset.cjs
- Layout Patterns
- Tailwind Integration
- radius
- Layout Patterns
- test_tailwind_config_gen.py
- routers/admin.py
- brand/references/update.md
- Logo Design Reference
- Token Architecture
- design-tokens-starter.json
- Primitive Tokens
- validate-tokens.cjs
- card
- .check_shadcn_config
- .generate_config_string
- Core Visual Elements
- inject-brand-context.cjs
- CIP Design Style Guide
- logo/generate.py
- embed-tokens.cjs
- ShadcnInstaller
- patch
- test_text_layout_resilience.py
- Quick Reference
- ._base_config
- Brand
- Slide Strategies
- Component Tokens
- generate-tokens.cjs
- button
- duration
- Slide Strategies
- CreateMesocycleSheet.tsx
- BarbellPlates.tsx
- sync-brand-to-tokens.cjs
- _run
- graphify reference: extra exports and benchmark
- input
- _row_identities
- UI/UX Pro Max - Design Intelligence
- Slides Reference
- HTML Slide Template
- HTML Slide Template
- Query Contract
- graphify reference: query, path, explain
- Slides
- Pre-Delivery Checklist
- Prerequisites
- Brand Guidelines Template
- $type
- radius
- lg
- sm
- Common Rules for Professional UI
- Example Workflow
- _AuditLogHandler
- cargar_pdf.py
- slide-token-validator.py
- padding-y
- xl
- none
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- migrate_uploads_to_storage.py
- Tips for Better Results
- test_sync_brand_to_tokens.py
- 16
- 1
- 3
- 8
- destructive
- destructive-foreground
- muted
- primary-foreground
- ring
- secondary-foreground
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- .__init__
- .temp_project
- CLAUDE.md
- .claude/CLAUDE.md
- slides-create.md
- extraction-spec.md
- create.md
- .test_add_components_no_config
- .test_add_components_dry_run
- .test_list_installed_no_config
- .test_init_dry_run
- .test_check_shadcn_config_not_exists
- .test_get_installed_components_empty
- .test_get_installed_components_with_files
- .test_add_components_no_components
- .test_add_colors_multiple_times
- .test_add_fonts
- .test_add_spacing
- .test_add_breakpoints
- .test_add_plugins_no_duplicates
- .test_recommend_plugins
- .test_recommend_plugins_nextjs
- .test_generate_typescript_config
- .test_generate_javascript_config
- .test_generate_config_with_colors
- .test_write_config
- .test_write_config_creates_content
- .test_default_content_paths_react
- .test_default_content_paths_nextjs
- .test_add_colors
- brand.ts
- _select_palette_for_mode

## God Nodes (most connected - your core abstractions)
1. `Session` - 119 edges
2. `apiFetch()` - 92 edges
3. `TailwindConfigGenerator` - 58 edges
4. `SanitizedModel` - 57 edges
5. `cx()` - 47 edges
6. `search()` - 43 edges
7. `react` - 41 edges
8. `useCurrentUser()` - 40 edges
9. `TestTailwindConfigGenerator` - 35 edges
10. `search_stack()` - 35 edges

## Surprising Connections (you probably didn't know these)
- `TestBm25CoreBehavior` --uses--> `BM25`  [INFERRED]
  .claude/skills/ui-ux-pro-max/scripts/tests/test_core.py → .claude/skills/design/scripts/cip/core.py
- `TestTokenizer` --uses--> `BM25`  [INFERRED]
  .claude/skills/ui-ux-pro-max/scripts/tests/test_core.py → .claude/skills/design/scripts/cip/core.py
- `TestShadcnInstaller` --uses--> `ShadcnInstaller`  [INFERRED]
  .claude/skills/ui-styling/scripts/tests/test_shadcn_add.py → .claude/skills/ui-styling/scripts/shadcn_add.py
- `TestGeneratedConfigIsValidJs` --uses--> `TailwindConfigGenerator`  [INFERRED]
  .claude/skills/ui-styling/scripts/tests/test_tailwind_config_gen.py → .claude/skills/ui-styling/scripts/tailwind_config_gen.py
- `TestTailwindConfigGenerator` --uses--> `TailwindConfigGenerator`  [INFERRED]
  .claude/skills/ui-styling/scripts/tests/test_tailwind_config_gen.py → .claude/skills/ui-styling/scripts/tailwind_config_gen.py

## Import Cycles
- None detected.

## Communities (237 total, 34 thin omitted)

### Community 0 - "AppShell.tsx"
Cohesion: 0.07
Nodes (44): ADMIN_NAV, AppShell(), ATHLETE_NAV, COACH_NAV, EXACT_ROUTES, INDEPENDENT_COACH_NAV, navFor(), NavItem (+36 more)

### Community 1 - "ui.tsx"
Cohesion: 0.11
Nodes (42): react, react-router-dom, PageHeader(), CoverThumbnail(), IconChevronRight(), IconStore(), SessionSetsEditor(), Badge() (+34 more)

### Community 2 - "validate_accent"
Cohesion: 0.33
Nodes (5): _luminance(), field_validator, Luminancia relativa WCAG 2.x — misma fórmula que web/src/lib/brand.ts., El acento también se usa como color de texto sobre el fondo carbón (#121212):…, validate_accent()

### Community 3 - "routers/plans.py"
Cohesion: 0.08
Nodes (53): upgrade(), Mesocycle, acquire_plan(), add_set_to_plan_session(), _can_see_plan(), create_plan(), delete_plan(), delete_plan_cover() (+45 more)

### Community 4 - "package.json"
Cohesion: 0.05
Nodes (39): @fontsource-variable/inter, react-dom, tailwindcss, @tailwindcss/vite, @types/node, @types/react, @types/react-dom, typescript (+31 more)

### Community 5 - "BoxHome.tsx"
Cohesion: 0.05
Nodes (54): daysLeft(), longDay(), PricingGrid(), SUBSCRIPTION_LABEL, SUBSCRIPTION_TONE, SubscriptionCard(), boxKeys, useAdminBoxes() (+46 more)

### Community 6 - "types.ts"
Cohesion: 0.05
Nodes (63): coachKeys, useAddPlanSet(), useDeletePlanSet(), useSetPlanSessionWodFormat(), useUpdatePlan(), useUpdatePlanSessionMeta(), CompleteSessionVars, LogSetVars (+55 more)

### Community 7 - "Session"
Cohesion: 0.08
Nodes (67): Group, Session, Set, get_or_create_exercise(), Usado por groups.py (bulk add/update de ejercicios), sessions.py (adaptar…, ensure_athletes_addable(), get_owned_group(), User (+59 more)

### Community 8 - "test_design_system_mode.py"
Cohesion: 0.14
Nodes (11): _filter_anti_patterns_for_mode(), _query_wants_dark(), True when a styles.csv row describes itself as dark-first., True when the query explicitly asks for a dark theme., Resolve the mode the rest of the output has to agree with., Drop "avoid dark mode" advice once dark mode is the resolved answer., _resolve_color_mode(), _style_is_dark_primary() (+3 more)

### Community 9 - "dates.ts"
Cohesion: 0.10
Nodes (34): IconBack(), TrainingCalendar(), WEEKDAY_LABELS, useDeleteMesocycle(), CalendarCell, daysFromToday(), DIAS, DIAS_CORTOS (+26 more)

### Community 10 - "models.py"
Cohesion: 0.06
Nodes (59): Backfill de una sola vez: llena users.coach_id para atletas que ya existian…, main(), Backfill de una sola vez: sincroniza Fit Level <-> "Récords (PRs)" para datos…, create_access_token(), ensure_owner_or_coach_editable(), get_current_user(), _ip_and_user_key(), _optional_current_user() (+51 more)

### Community 11 - "validate_data.py"
Cohesion: 0.10
Nodes (43): Semantic quality contracts for the core UI/UX datasets., TestChartsTypographyAndIcons, _catalog_date(), _check_app_interface_contract(), _check_catalog_contract(), _check_catalog_summary(), _check_chart_contract(), _check_color_contract() (+35 more)

### Community 12 - "cip/core.py"
Cohesion: 0.06
Nodes (46): BM25, detect_domain(), get_cip_brief(), _load_csv(), Load CSV and return list of dicts, Core search function using BM25, Auto-detect the most relevant domain from query, Main search function with auto-domain detection (+38 more)

### Community 13 - "gray"
Cohesion: 0.05
Nodes (53): $type, $value, $type, $value, $type, $value, $type, $value (+45 more)

### Community 14 - "_build_smart_mesocycle"
Cohesion: 0.11
Nodes (28): adapt_session_to_time(), _generate_json_with_fallback(), generate_mesocycle_chunk(), generate_workout_session(), _post_to_gemini(), `literatura_cientifica` se calcula UNA sola vez por mesociclo…, Toma los ejercicios YA prescritos para una sesión y los adapta (menos series,…, Delimita un campo libre (escrito por un coach o un atleta) dentro del prompt… (+20 more)

### Community 15 - "slide_search_core.py"
Cohesion: 0.08
Nodes (38): format_context(), format_result(), main(), Format a single search result for display, Slide Search CLI - Search slide design databases for strategies, layouts, copy,…, Format contextual recommendations for display., BM25, calculate_pattern_break() (+30 more)

### Community 16 - "FitLevel.tsx"
Cohesion: 0.16
Nodes (12): FitLevel, FitLevelCriteria(), Segmented(), useSaveBenchmarks(), FitCategory, WodCategory, CAT_LABEL, FitLevel() (+4 more)

### Community 17 - "compilerOptions"
Cohesion: 0.09
Nodes (21): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleDetection (+13 more)

### Community 18 - "apiFetch"
Cohesion: 0.07
Nodes (43): IconUser(), apiFetch(), useAddGroupMembers(), useAthleteLeaderboard(), useAthletes(), useCreateGroup(), useDeleteGroup(), useGroupDetail() (+35 more)

### Community 19 - "routers/users.py"
Cohesion: 0.08
Nodes (45): _coach_athlete_ids(), ensure_owner_or_coach(), User, UUID, Dueño de un box (cualquier estado del box: un dueño con el box pendiente sí…, Dependencia para endpoints reservados exclusivamente al rol 'admin'., IDs de los atletas que este coach puede gestionar. Es la definición única de…, Verifica que el usuario autenticado sea el dueño del recurso, un admin, o un… (+37 more)

### Community 20 - "Tailwind CSS Utility Reference"
Cohesion: 0.05
Nodes (43): Arbitrary Values, Aspect Ratio, Background Colors, Border Color, Border Radius, Border Style, Border Width, Borders (+35 more)

### Community 21 - "Brand Guidelines v1.0"
Cohesion: 0.05
Nodes (37): 1. Color Palette, 2. Typography, 3. Logo Usage, 4. Voice & Tone, 5. Imagery Guidelines, 6. Design Components, Accessibility, AI Image Generation (+29 more)

### Community 22 - "GroupProgramDetail.tsx"
Cohesion: 0.05
Nodes (66): BlockSelect(), SessionCard(), AddExerciseForm(), BlockOrderEditor(), ExerciseBlock(), TipoCarga, WarmupNotesCard(), SetRow() (+58 more)

### Community 23 - "fitness_scoring.py"
Cohesion: 0.22
Nodes (12): _age_multiplier(), _bounds_for(), compute_fitness_level(), Calculadora de 'Fit Level' para CrossFit: halterofilia, gimnasia y metcon.…, values: {metric_key: value} solo con las métricas que el atleta ya registró., bounds = [max_principiante, max_intermedio, max_avanzado] (ascendente)., bounds = [max_elite, max_avanzado, max_intermedio] (ascendente, en segundos)., Cuánto se 'relajan' los estándares por edad (1.0 = sin ajuste, edades <=35).… (+4 more)

### Community 24 - "Design"
Cohesion: 0.06
Nodes (35): Banner Design (Built-in), Banner: Design Rules, Banner: Quick Size Reference, Banner: Top Art Styles, Banner: Workflow, CIP Design (Built-in), CIP: Generate Brief, CIP: Generate Mockups (+27 more)

### Community 25 - "avatars.py"
Cohesion: 0.23
Nodes (10): AvatarRejected, HTTPException, UploadFile, Validación y saneo de imágenes subidas por el usuario (avatar, portada de…, Identifica el formato real por su firma binaria. Devuelve None si no coincide…, Lee el archivo del request respetando el límite de tamaño DESDE la lectura…, Decodifica la imagen y la reconstruye en un lienzo completamente nuevo,…, read_and_validate_upload() (+2 more)

### Community 26 - "Canvas Design System"
Cohesion: 0.06
Nodes (35): 1. Visual Communication First, 2. Minimal Text Integration, 3. Expert Craftsmanship, 4. Systematic Patterns, Analog Meditation, Approach, Canvas Boundaries, Canvas Design System (+27 more)

### Community 27 - "Form & Input Components"
Cohesion: 0.06
Nodes (32): Accordion, Alert, Alert Dialog, Avatar, Badge, Button, Card, Checkbox (+24 more)

### Community 28 - "routers/boxes.py"
Cohesion: 0.06
Nodes (64): athletes_count(), ensure_can_add_athlete(), max_athletes(), Planes de suscripción. La unidad que paga es la CUENTA (tabla boxes): un box, o…, active" (pagado y vigente) | "trial" (en periodo de prueba) | "expired". Un…, Se llama en TODO camino por el que un atleta nuevo entra a una cuenta…, subscription_status(), trial_end_from() (+56 more)

### Community 29 - "Tailwind CSS Responsive Design"
Cohesion: 0.06
Nodes (32): 1. Mobile-First Design, 2. Consistent Breakpoint Usage, 3. Test at Breakpoint Boundaries, 4. Use Container for Content Width, 5. Progressive Enhancement, 6. Avoid Too Many Breakpoints, Best Practices, Breakpoint System (+24 more)

### Community 30 - "env.py"
Cohesion: 0.40
Nodes (4): Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online()

### Community 31 - "App.tsx"
Cohesion: 0.07
Nodes (49): @tanstack/react-query, App(), COACH_ROLES, homeForRole(), RedirectIfLogged(), RequireAppAccess(), RoleGate(), RootRoute() (+41 more)

### Community 32 - "search_stack"
Cohesion: 0.10
Nodes (8): Search stack-specific guidelines, search_stack(), Freshness and migration contracts for native, desktop, and 3D stacks., _rows(), TestNativeDesktopStackFreshness, Freshness and generation-isolation contracts for web stack guidance., _rows(), TestWebStackFreshness

### Community 33 - "Typography Specifications"
Cohesion: 0.06
Nodes (30): Accessibility, Base System, Best Practices, Clean & Modern, Common Font Pairings, Contrast Requirements, CSS Implementation, Editorial (+22 more)

### Community 34 - "TestTailwindConfigGenerator"
Cohesion: 0.06
Nodes (16): Test TailwindConfigGenerator class., Test initialization with default settings., Test generating config with plugins., Test validating valid configuration., Test validating config with no content paths., Test validating config with empty theme extensions., Test initialization for JavaScript config., Test writing config to invalid path. (+8 more)

### Community 35 - "search"
Cohesion: 0.11
Nodes (8): Resolve a deprecated in-domain alias, or expose a cross-domain redirect., Main search function with auto-domain detection, search(), _style_search_destination(), TestSearchDomains, Regression tests for the public style taxonomy and search contract., read_rows(), TestStyleTaxonomy

### Community 51 - "Logo Usage Rules"
Cohesion: 0.07
Nodes (28): Absolute Don'ts, Approved Backgrounds, Before Using Logo, Clear Space, Co-branding, Color Rules, Color Usage, Color Variants (+20 more)

### Community 52 - "Component Specifications"
Cohesion: 0.07
Nodes (28): Alert, Anatomy, Anatomy, Anatomy, Anatomy, Anatomy, Badge, Button (+20 more)

### Community 53 - "html-token-validator.py"
Cohesion: 0.12
Nodes (25): get_context(), is_allowed_exception(), is_allowed_rgba(), is_inside_block(), load_css_variables(), main(), print_result(), print_summary() (+17 more)

### Community 54 - "shadcn/ui Accessibility Patterns"
Cohesion: 0.07
Nodes (28): Accordion, Alert, ARIA Labels, Checkbox and Radio, Color Contrast, Command Palette Navigation, Component-Specific Patterns, Dialog/Modal Navigation (+20 more)

### Community 55 - "scripts/core.py"
Cohesion: 0.11
Nodes (28): _contains_phrase(), _domain_keywords(), _exact_stack_identifier(), _file_signature(), _get_bm25(), _load_csv(), _load_csv_snapshot(), _load_product_keywords() (+20 more)

### Community 56 - "logo/core.py"
Cohesion: 0.10
Nodes (21): BM25, detect_domain(), _load_csv(), Load CSV and return list of dicts, Core search function using BM25, Auto-detect the most relevant domain from query, Main search function with auto-domain detection, Search across all domains and combine results (+13 more)

### Community 57 - "What You Must Do When Invoked"
Cohesion: 0.07
Nodes (26): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+18 more)

### Community 58 - "Asset Approval Checklist"
Cohesion: 0.08
Nodes (25): Accessibility, Archival, Asset Approval Checklist, Automation Support, Color Compliance, Common Issues & Fixes, Content Accessibility, Content Quality (+17 more)

### Community 59 - "Logo AI Prompt Engineering"
Cohesion: 0.08
Nodes (25): Common Pitfalls, Core Prompt Structure, Detailed Brief, Eco/Sustainable, Effective Keywords by Style, Fashion Brand, Healthcare, Industry-Specific Prompts (+17 more)

### Community 60 - "design_system.py"
Cohesion: 0.07
Nodes (32): ansi_ljust(), _detect_page_type(), format_ascii_box(), format_markdown(), format_master_md(), format_page_override_md(), generate_design_system(), _generate_intelligent_overrides() (+24 more)

### Community 61 - "Color Palette Management"
Cohesion: 0.08
Nodes (24): Accessibility Requirements, Brand Compliance Validation, Checking Contrast, Color Documentation Format, Color Extraction, Color Palette Examples, Color Palette Management, Color System Structure (+16 more)

### Community 62 - "CIP Deliverable Guide"
Cohesion: 0.08
Nodes (24): Apparel, Business Card, Car/Sedan, CIP Deliverable Guide, Core Identity, Digital Assets, Email Signature, Envelope (+16 more)

### Community 63 - "States and Variants"
Cohesion: 0.08
Nodes (24): Accessibility, Accessibility Requirements, ARIA States, Color Contrast, Color Variants, Disabled States, Error Messages, Error States (+16 more)

### Community 64 - "UI Styling Skill"
Cohesion: 0.08
Nodes (24): Accessibility Patterns, Alternative: Tailwind-Only Setup, Best Practices, Common Patterns, Component Layer: shadcn/ui, Component Library Guide, Component + Styling Setup, Core Stack (+16 more)

### Community 65 - "test_data_contracts.py"
Cohesion: 0.11
Nodes (13): apply_decision_rules(), _object_without_duplicates(), parse_decision_rules(), Return deterministic mutations and an audit trail; never execute data., Closed, non-executable grammar for design-system decision rules., Parse the canonical condition -> action-array representation., _validate_action(), Cross-file semantic contracts for curated design data. (+5 more)

### Community 66 - "Workflow"
Cohesion: 0.08
Nodes (23): Art Direction Styles (Reuse from Banner), Color & Contrast, Design Best Practices, HTML Design Rules, HTML Template Structure, Option A: Chrome Headless CLI (Recommended — zero dependencies), Option B: chrome-devtools skill, Option C: Playwright script (+15 more)

### Community 68 - "DesignSystemGenerator"
Cohesion: 0.08
Nodes (15): DesignSystemGenerator, Generates design system recommendations from aggregated searches., Load reasoning rules from CSV., Execute searches across multiple domains., Find matching reasoning rule for a category., Apply reasoning rules to search results., Select best matching result based on priority keywords., Extract results list from search result dict. (+7 more)

### Community 70 - "Design System"
Cohesion: 0.09
Nodes (22): Best Practices, Chart.js Integration, Command, Component Spec Pattern, Contextual Decision Flow, Decision System CSVs, Design System, Integration (+14 more)

### Community 71 - "Tailwind CSS Customization"
Cohesion: 0.09
Nodes (22): @apply Directive, Best Practices, Color Customization, Complete Tailwind Config, Configuration Examples, Content Configuration, Custom Color Palette, Custom Font Sizes (+14 more)

### Community 72 - "spacing"
Cohesion: 0.09
Nodes (22): $type, $value, $type, $value, $type, $value, $type, $value (+14 more)

### Community 73 - "TailwindConfigGenerator"
Cohesion: 0.09
Nodes (12): Add custom font families. Args: fonts: Dict of font_type: [font_names] e.g.,…, Add custom spacing values. Args: spacing: Dict of name: value e.g., {'18':…, Add custom breakpoints. Args: breakpoints: Dict of name: width e.g., {'3xl':…, Add plugin requirements. Args: plugins: List of plugin names e.g.,…, Get plugin recommendations based on configuration. Returns: List of recommended…, Generate Tailwind CSS configuration files., Validate configuration. Returns: Tuple of (valid, message), Add custom colors to theme. Args: colors: Dict of color_name: color_value Value… (+4 more)

### Community 74 - "AvatarUploader.tsx"
Cohesion: 0.10
Nodes (24): ACCEPTED_TYPES, BoxLogo(), ACCEPTED_TYPES, CoverUploader(), handleFileChange(), IconCamera(), IconTrash(), Spinner() (+16 more)

### Community 75 - "schemas/__init__.py"
Cohesion: 0.03
Nodes (121): clean_text(), Sanea un texto libre antes de guardarlo: quita cualquier HTML/script (bleach,…, AdminOverview, AuditLogResponse, Config, BaseModel, Solo un admin puede cambiar el rol de un usuario (incluyendo promover a otro…, UserRoleUpdate (+113 more)

### Community 76 - "logging_http_exception_handler"
Cohesion: 0.25
Nodes (8): add_security_headers(), logging_http_exception_handler(), HTTPException, Request, Registra intentos de acceso no autorizados (401/403) para poder auditarlos…, Cabeceras de seguridad HTTP estándar (defensa en profundidad; esta API solo…, exception_handler, middleware

### Community 77 - "generate-slide.py"
Cohesion: 0.14
Nodes (20): _e(), generate_chart_slide(), generate_cta_slide(), generate_deck(), generate_metrics_slide(), generate_problem_slide(), generate_solution_slide(), generate_testimonial_slide() (+12 more)

### Community 78 - "wodFormatUsesTimeCap"
Cohesion: 0.17
Nodes (10): WodBlockCard(), elegir(), guardarFormato(), wodFormatUsesTimeCap(), BulkWodBlockCard(), elegir(), guardarFormato(), PlanWodBlockCard() (+2 more)

### Community 79 - "read_rows"
Cohesion: 0.21
Nodes (4): read_rows(), TestAccessibilityGuidance, TestCurrentReactGuidance, TestSemanticColors

### Community 80 - "adapt_session_to_available_time"
Cohesion: 0.14
Nodes (21): adapt_session_to_available_time(), complete_session(), create_session(), delete_session(), delete, limit, post, put (+13 more)

### Community 81 - "Routing by Task Type"
Cohesion: 0.10
Nodes (19): Banner Design Tasks, Brand Identity Tasks, Component Creation, Corporate Identity Program Tasks, Design Routing Guide, Design System Migration, Icon Design Tasks, Implementation Tasks (+11 more)

### Community 82 - "shadcn/ui Theming & Customization"
Cohesion: 0.10
Nodes (19): Base Color Presets, Best Practices, Color Customization, Color Format, Component Customization, CSS Variable System, Customize Styles, Customize Variants (+11 more)

### Community 83 - "Asset Organization Guide"
Cohesion: 0.11
Nodes (18): Asset Entry (manifest.json), Asset Organization Guide, By Campaign, By Status, By Type, Cleanup Workflow, Components, Directory Structure (+10 more)

### Community 84 - "Primary Color Meanings"
Cohesion: 0.11
Nodes (18): Accessibility Considerations, Analogous, Black, Blue, Color Combinations by Industry, Color Harmony Types, Complementary, Green (+10 more)

### Community 85 - "Core Logo Types"
Cohesion: 0.11
Nodes (18): 1. Wordmark (Logotype), 2. Lettermark (Monogram), 3. Pictorial Mark (Brand Mark), 4. Abstract Mark, 5. Mascot, 6. Emblem, 7. Combination Mark, Aesthetic Styles (+10 more)

### Community 86 - "fetch-background.py"
Cohesion: 0.16
Nodes (18): generate_css_for_background(), get_background_image(), get_curated_images(), get_overlay_css(), get_pexels_search_url(), load_backgrounds_config(), load_brand_colors(), main() (+10 more)

### Community 87 - "color"
Cohesion: 0.11
Nodes (19): $type, $value, background, foreground, muted-foreground, primary, primary-hover, secondary (+11 more)

### Community 88 - "Brand Consistency Checklist"
Cohesion: 0.11
Nodes (17): Audit Frequency, Brand Consistency Checklist, Channel Audit, Collateral, Colors, Common Issues, Email, Imagery (+9 more)

### Community 89 - "CIP Mockup Prompt Engineering"
Cohesion: 0.11
Nodes (17): Apparel (Polo/T-Shirt), Base Prompt Structure, Business Card, CIP Mockup Prompt Engineering, Context Modifiers, Corporate Minimal, Deliverable-Specific Modifiers, Letterhead (+9 more)

### Community 90 - "Color Semantics"
Cohesion: 0.11
Nodes (17): Accent, Applying Semantic Tokens, Background & Foreground, Border & Ring, Color Semantics, Dark Mode Overrides, Destructive, Interactive States (+9 more)

### Community 91 - "TestThresholdGate"
Cohesion: 0.12
Nodes (4): Unit tests for metric math and relevance fixture validation., TestFixtureValidation, TestMetricMath, TestThresholdGate

### Community 92 - "icon/generate.py"
Cohesion: 0.18
Nodes (16): apply_color(), apply_viewbox_size(), extract_svgs(), generate_batch(), generate_icon(), generate_sizes(), load_env(), main() (+8 more)

### Community 93 - "BM25"
Cohesion: 0.10
Nodes (10): BM25, BM25 ranking algorithm for text search, Lowercase, normalize synonyms, split, remove punctuation, filter stopwords, Build BM25 index from documents, Score all documents against query, All indexed terms, for suggestion/typo-recovery purposes., Stdlib-only regression tests for core.py / design_system.py (unittest, not…, TestBm25CoreBehavior (+2 more)

### Community 95 - "schemas/mesocycles.py"
Cohesion: 0.09
Nodes (30): _build_manual_mesocycle(), create_manual_mesocycle(), create_manual_mesocycle_for_group(), create_mesocycle(), delete_mesocycle(), get_full_mesocycle(), listar_mesociclos(), delete (+22 more)

### Community 96 - "_normalize"
Cohesion: 0.22
Nodes (9): _exact_match_diagnostic(), _legacy_successor_guidance(), _normalize(), Apply longest-first synonym substitution at token boundaries., Whether a stack query explicitly targets an older framework generation., Choose one coherent applicability generation for stack retrieval., Prefer the explicit successor row for a brand-new app on legacy-only stacks., _stack_query_requests_legacy() (+1 more)

### Community 97 - "Design Principles"
Cohesion: 0.12
Nodes (15): 22 Art Direction Styles, Banner Sizes & Art Direction Styles Reference, Complete Banner Sizes, CTA Rules, Design Principles, Pinterest Research Queries, Print, Print Specs (+7 more)

### Community 98 - "Design Principles"
Cohesion: 0.12
Nodes (15): 22 Art Direction Styles, Banner Sizes & Art Direction Styles Reference, Complete Banner Sizes, CTA Rules, Design Principles, Pinterest Research Queries, Print, Print Specs (+7 more)

### Community 99 - "fontSize"
Cohesion: 0.12
Nodes (16): $type, $value, $type, $value, $type, $value, $type, $value (+8 more)

### Community 100 - "TestShadcnInstaller"
Cohesion: 0.12
Nodes (9): Test ShadcnInstaller class., Test adding all components without config., Test adding all components in dry run mode., Test listing installed components when none exist., Test listing installed components when they exist., Test initialization with custom project root., Test checking for existing shadcn config., Test getting installed components without config. (+1 more)

### Community 101 - "CIP Design Reference"
Cohesion: 0.13
Nodes (14): CIP Brief (Start Here), CIP Design Reference, Commands, Deliverable Categories, Design Styles, Detailed References, Generate Mockups, HTML Presentation Features (+6 more)

### Community 102 - "Icon Design Reference"
Cohesion: 0.13
Nodes (14): Available Styles, CLI Options, Commands, Generate Batch Variations, Generate Multiple Sizes, Generate Single Icon, Icon Categories, Icon Design Reference (+6 more)

### Community 103 - "Copywriting Formulas"
Cohesion: 0.13
Nodes (14): AIDA (Attention-Interest-Desire-Action), Before-After-Bridge, Contrast Patterns, Copywriting Formulas, Core Formulas, Cost of Inaction, FAB (Features-Advantages-Benefits), Formula-to-Slide Mapping (+6 more)

### Community 104 - "Copywriting Formulas"
Cohesion: 0.13
Nodes (14): AIDA (Attention-Interest-Desire-Action), Before-After-Bridge, Contrast Patterns, Copywriting Formulas, Core Formulas, Cost of Inaction, FAB (Features-Advantages-Benefits), Formula-to-Slide Mapping (+6 more)

### Community 105 - "detect_domain"
Cohesion: 0.23
Nodes (3): detect_domain(), Auto-detect the most relevant domain from query. Matches are weighted by…, TestDomainDetection

### Community 106 - "RegisterAthleteSheet"
Cohesion: 1.00
Nodes (3): RegisterAthleteSheet(), handleSubmit(), reset()

### Community 110 - "Banner Design - Multi-Format Creative Banner System"
Cohesion: 0.14
Nodes (13): Art Direction Styles (Top 10), Banner Design - Multi-Format Creative Banner System, Banner Size Quick Reference, Design Rules, Prerequisites, Security, Step 1: Gather Requirements (AskUserQuestion), Step 2: Research & Art Direction (+5 more)

### Community 111 - "Messaging Framework"
Cohesion: 0.14
Nodes (13): Core Statements, Elevator Pitches, Framework Structure, Message Architecture, Message by Audience, Message Testing, Messaging Framework, Mission Statement (+5 more)

### Community 112 - "Brand Voice Framework"
Cohesion: 0.14
Nodes (13): Brand Voice Framework, Character Spectrum, Emotion Spectrum, Language Spectrum, Step 1: Define Personality Traits, Step 2: Create Voice Chart, Step 3: Context Adaptation, Tone Spectrum (+5 more)

### Community 113 - "extract-colors.cjs"
Cohesion: 0.22
Nodes (11): calculateCompliance(), colorDistance(), displayPalette(), extractHexColors(), findNearestBrandColor(), fs, generateImageMagickCommand(), hexToRgb() (+3 more)

### Community 114 - "validate-asset.cjs"
Cohesion: 0.25
Nodes (13): checkManifest(), formatBytes(), formatOutput(), fs, main(), parseFilename(), path, RULES (+5 more)

### Community 115 - "Layout Patterns"
Cohesion: 0.14
Nodes (13): Card Styles, Component Variants, CSS Structures, Feature Grid (3 columns), Layout Decision Flow, Layout Patterns, Layout Selection by Use Case, Metric Styles (+5 more)

### Community 116 - "Tailwind Integration"
Cohesion: 0.14
Nodes (13): Animation Tokens, Base Layer, Button Example, Component Classes, CSS Variables Setup, Dark Mode Toggle, HSL Format Benefits, shadcn/ui Alignment (+5 more)

### Community 117 - "radius"
Cohesion: 0.19
Nodes (14): $type, $value, $type, $value, $type, $value, primitive, radius (+6 more)

### Community 118 - "Layout Patterns"
Cohesion: 0.14
Nodes (13): Card Styles, Component Variants, CSS Structures, Feature Grid (3 columns), Layout Decision Flow, Layout Patterns, Layout Selection by Use Case, Metric Styles (+5 more)

### Community 119 - "test_tailwind_config_gen.py"
Cohesion: 0.16
Nodes (10): main(), Tailwind CSS Configuration Generator Generate tailwind.config.js/ts with custom…, Tests for tailwind_config_gen.py, Reduce a generated TS/JS config to a bare assignable object so it can be handed…, Regression guard for the missing-comma bug between the ``theme`` block and…, The property preceding ``plugins`` must end with a comma (pure-Python check, so…, The emitted config parses as valid JS via ``node --check``., _strip_to_object() (+2 more)

### Community 120 - "routers/admin.py"
Cohesion: 0.18
Nodes (19): get_admin_overview(), get_audit_logs(), get, post, put, User, UUID, Historial de eventos de seguridad (logins fallidos, cambios de rol,… (+11 more)

### Community 122 - "brand/references/update.md"
Cohesion: 0.15
Nodes (12): Color Presets, Examples, Files Modified, Important, Overview, Skills Used, Step 1: Gather Brand Input, Step 2: Update Brand Guidelines (+4 more)

### Community 123 - "Logo Design Reference"
Cohesion: 0.15
Nodes (12): Available Styles, Color Psychology, Commands, Design Brief (Start Here), Detailed References, Generate Logo, Industry Defaults, Logo Design Reference (+4 more)

### Community 124 - "Token Architecture"
Cohesion: 0.15
Nodes (12): Categories, Dark Mode, File Organization, Layer 1: Primitive Tokens, Layer 2: Semantic Tokens, Layer 3: Component Tokens, Layer Overview, Migration from Flat Tokens (+4 more)

### Community 125 - "design-tokens-starter.json"
Cohesion: 0.15
Nodes (12): component, $type, $value, dark, semantic, $schema, $type, $value (+4 more)

### Community 127 - "Primitive Tokens"
Cohesion: 0.17
Nodes (11): Border Radius, Color Scales, Gray Scale, Motion / Duration, Primary Colors (Blue), Primitive Tokens, Shadows, Spacing Scale (+3 more)

### Community 128 - "validate-tokens.cjs"
Cohesion: 0.26
Nodes (11): extensions, formatReport(), fs, getFiles(), main(), parseArgs(), path, patterns (+3 more)

### Community 129 - "card"
Cohesion: 0.20
Nodes (12): $type, $value, bg, bg, padding, shadow, card, bg (+4 more)

### Community 130 - ".check_shadcn_config"
Cohesion: 0.21
Nodes (6): Add all available shadcn/ui components. Args: overwrite: If True, overwrite…, List installed components. Returns: Tuple of (success, message with component…, Check if shadcn is initialized in project. Returns: True if components.json…, Get list of already installed components. Returns: List of installed component…, Read shadcn version from project package.json; fall back to a pinned default., Add shadcn/ui components. Args: components: List of component names to add…

### Community 131 - ".generate_config_string"
Cohesion: 0.20
Nodes (6): Generate configuration file content. Returns: Configuration file as string, Generate TypeScript configuration., Generate JavaScript configuration., Format plugins array for config. Validates each plugin name against a strict…, Add indentation to JSON string., Write configuration to file. Returns: Tuple of (success, message)

### Community 132 - "Core Visual Elements"
Cohesion: 0.18
Nodes (10): Color Palette, Colors, Core Visual Elements, Logo, Logo, Quick Checks, Typography, Typography (+2 more)

### Community 133 - "inject-brand-context.cjs"
Cohesion: 0.31
Nodes (10): extractColorsFromTable(), extractCoreAttributes(), extractHexColors(), extractImageStyle(), extractTypography(), extractVoice(), fs, generatePromptAddition() (+2 more)

### Community 134 - "CIP Design Style Guide"
Cohesion: 0.18
Nodes (10): Bold Dynamic, CIP Design Style Guide, Classic Traditional, Color Psychology, Corporate Minimal, Fresh Modern, Luxury Premium, Modern Tech (+2 more)

### Community 135 - "logo/generate.py"
Cohesion: 0.25
Nodes (10): enhance_prompt(), generate_batch(), generate_logo(), load_env(), main(), Enhance the logo prompt with style and industry modifiers, Generate a logo using Gemini models with image generation Args: aspect_ratio:…, Generate multiple logo variants with different styles (+2 more)

### Community 136 - "embed-tokens.cjs"
Cohesion: 0.18
Nodes (8): args, fs, minimal, MINIMAL_TOKENS, path, projectRoot, tokensPath, wrapStyle

### Community 137 - "ShadcnInstaller"
Cohesion: 0.22
Nodes (7): main(), Handle shadcn/ui component installation., shadcn/ui Component Installer Add shadcn/ui components to project with…, ShadcnInstaller, Tests for shadcn_add.py, Test adding components that are already installed., Test initialization with default project root.

### Community 138 - "patch"
Cohesion: 0.18
Nodes (6): Test adding components with overwrite flag., Test successful component addition., Test component addition with subprocess error., Test component addition when npx is not found., Test successful addition of all components., patch

### Community 139 - "test_text_layout_resilience.py"
Cohesion: 0.20
Nodes (4): Canonical regression contracts for resilient UI text layouts., read_rows(), TestTextLayoutDataContracts, TestTextLayoutRetrieval

### Community 140 - "Quick Reference"
Cohesion: 0.18
Nodes (11): 10. Charts & Data (LOW), 1. Accessibility (CRITICAL), 2. Touch & Interaction (CRITICAL), 3. Performance (HIGH), 4. Style Selection (HIGH), 5. Layout & Responsive (HIGH), 6. Typography & Color (MEDIUM), 7. Animation (MEDIUM) (+3 more)

### Community 141 - "._base_config"
Cohesion: 0.22
Nodes (6): Any, Path, Initialize generator. Args: typescript: If True, generate .ts config, else .js…, Determine default output path., Create base configuration structure., Get default content paths for framework.

### Community 142 - "Brand"
Cohesion: 0.20
Nodes (9): Brand, Brand Sync Workflow, Quick Start, References, Routing, Scripts, Subcommands, Templates (+1 more)

### Community 143 - "Slide Strategies"
Cohesion: 0.20
Nodes (9): Common Structures, Duarte Sparkline Pattern, Matching Strategy to Context, Product Demo (6 slides), Sales Pitch (9 slides), Search Commands, Slide Strategies, Strategy Selection (+1 more)

### Community 144 - "Component Tokens"
Cohesion: 0.20
Nodes (9): Alert Tokens, Badge Tokens, Button Tokens, Card Tokens, Component Tokens, Dialog/Modal Tokens, Input Tokens, Table Tokens (+1 more)

### Community 145 - "generate-tokens.cjs"
Cohesion: 0.40
Nodes (9): flattenTokens(), fs, generateCSS(), generateTailwind(), main(), parseArgs(), path, resolveReference() (+1 more)

### Community 146 - "button"
Cohesion: 0.20
Nodes (10): fg, font-size, hover-bg, button, $type, $value, $type, $value (+2 more)

### Community 147 - "duration"
Cohesion: 0.20
Nodes (10): fast, normal, slow, $type, $value, $type, $value, duration (+2 more)

### Community 148 - "Slide Strategies"
Cohesion: 0.20
Nodes (9): Common Structures, Duarte Sparkline Pattern, Matching Strategy to Context, Product Demo (6 slides), Sales Pitch (9 slides), Search Commands, Slide Strategies, Strategy Selection (+1 more)

### Community 149 - "CreateMesocycleSheet.tsx"
Cohesion: 0.21
Nodes (12): CreateMesocycleSheet(), handleSubmit(), reset(), DISCIPLINAS, DAYS, WEEKDAY_NAMES, WeekdayPicker(), useCreateManualMesocycle() (+4 more)

### Community 150 - "BarbellPlates.tsx"
Cohesion: 0.33
Nodes (8): BarbellPlates(), plateSize(), PlateStack(), barWeightKg(), calculatePlates(), PLATE_COLORS, PLATE_DENOMINATIONS_KG, PlateBreakdown

### Community 152 - "sync-brand-to-tokens.cjs"
Cohesion: 0.33
Nodes (8): adjustBrightness(), { execFileSync }, extractColorsFromMarkdown(), fs, generateColorScale(), main(), path, updateDesignTokens()

### Community 153 - "_run"
Cohesion: 0.28
Nodes (8): Path, Regression tests for validate-tokens.cjs. The validator used to skip any line…, A hardcoded hex on the same line as a var() token is still a violation., A line that references only tokens produces no false positives., _run(), test_flags_hardcoded_hex_sharing_line_with_token(), test_token_only_line_reports_no_violation(), CompletedProcess

### Community 154 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 155 - "input"
Cohesion: 0.29
Nodes (8): padding-x, input, $type, $value, focus-ring, padding-x, $type, $value

### Community 156 - "_row_identities"
Cohesion: 0.25
Nodes (8): _exact_row_identity(), Suggest complete public identities so a retry can bypass score thresholds., Return non-empty public identities from ordinary and alias fields., Resolve an explicit style identity without opening generic variant ranking., Return one row whose stable public identity exactly matches the query., _row_identities(), _style_identity(), _suggest_identities()

### Community 157 - "UI/UX Pro Max - Design Intelligence"
Cohesion: 0.25
Nodes (7): How to Use, Primary Use Cases, Recommended, Rule Categories by Priority, Skip, UI/UX Pro Max - Design Intelligence, When to Apply

### Community 159 - "Slides Reference"
Cohesion: 0.29
Nodes (6): Key Features, Knowledge Base, Slides Reference, Usage, When to Use, Workflow

### Community 160 - "HTML Slide Template"
Cohesion: 0.29
Nodes (6): Animation Classes, Background Images, Base Structure, Chart.js Integration, CSS Variables Reference, HTML Slide Template

### Community 161 - "HTML Slide Template"
Cohesion: 0.29
Nodes (6): Animation Classes, Background Images, Base Structure, Chart.js Integration, CSS Variables Reference, HTML Slide Template

### Community 162 - "Query Contract"
Cohesion: 0.29
Nodes (7): Query Contract, Step 1: Analyze User Requirements, Step 2: Generate Design System (new projects/pages), Step 2b: Persist Design System (Master + Overrides Pattern), Step 2c: Design Dials (optional), Step 3: Supplement with Detailed Searches (as needed), Step 4: Stack Guidelines

### Community 163 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 164 - "Slides"
Cohesion: 0.33
Nodes (5): References (Knowledge Base), Routing, Slides, Subcommands, When to Use

### Community 165 - "Pre-Delivery Checklist"
Cohesion: 0.33
Nodes (6): Accessibility, Interaction, Layout, Light/Dark Mode, Pre-Delivery Checklist, Visual Quality

### Community 166 - "Prerequisites"
Cohesion: 0.33
Nodes (6): Available Domains, Available Stacks, How to Use This Skill, Output Formats, Prerequisites, Search Reference

### Community 167 - "Brand Guidelines Template"
Cohesion: 0.40
Nodes (4): Brand Guidelines Template, Document Structure, Extractable Fields, Usage

### Community 168 - "$type"
Cohesion: 0.60
Nodes (5): $type, $value, border, border, border

### Community 169 - "radius"
Cohesion: 0.60
Nodes (5): radius, radius, radius, $type, $value

### Community 170 - "lg"
Cohesion: 0.60
Nodes (5): lg, $type, $value, lg, lg

### Community 171 - "sm"
Cohesion: 0.60
Nodes (5): sm, sm, sm, $type, $value

### Community 172 - "Common Rules for Professional UI"
Cohesion: 0.40
Nodes (5): Common Rules for Professional UI, Icons & Visual Elements, Interaction (App), Layout & Spacing, Light/Dark Mode Contrast

### Community 173 - "Example Workflow"
Cohesion: 0.40
Nodes (5): Example Workflow, Step 1: Analyze Requirements, Step 2: Generate Design System, Step 3: Supplement with Detailed Searches (as needed), Step 4: Stack Guidelines

### Community 174 - "_AuditLogHandler"
Cohesion: 0.50
Nodes (3): _AuditLogHandler, Espejo de security_logger en la tabla audit_logs (ver backend/models.py): antes…, LogRecord

### Community 175 - "cargar_pdf.py"
Cohesion: 0.67
Nodes (3): get_embedding(), process_and_upload_pdf(), Llama a Google Gemini para convertir un fragmento de texto en un vector…

### Community 176 - "slide-token-validator.py"
Cohesion: 0.50
Nodes (3): main(), Slide Token Validator (Legacy Wrapper) Now delegates to html-token-validator.py…, Delegate to unified html-token-validator.py with --type slides.

### Community 177 - "padding-y"
Cohesion: 0.67
Nodes (4): padding-y, padding-y, $type, $value

### Community 178 - "xl"
Cohesion: 0.67
Nodes (4): xl, xl, $type, $value

### Community 179 - "none"
Cohesion: 0.67
Nodes (4): $type, $value, none, none

### Community 180 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 181 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 182 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 183 - "migrate_uploads_to_storage.py"
Cohesion: 0.29
Nodes (6): main(), Sube a Supabase Storage lo que haya quedado en backend/uploads/ (del…, ensure_buckets(), Crea los buckets privados si todavía no existen. Idempotente: seguro de llamar…, Como upload_object, pero con una key EXPLÍCITA en vez de generar una nueva —…, upload_object_as()

### Community 184 - "Tips for Better Results"
Cohesion: 0.50
Nodes (4): Common Sticking Points, Pre-Delivery Checklist, Query Strategy, Tips for Better Results

### Community 194 - "16"
Cohesion: 0.67
Nodes (3): $type, $value, 16

### Community 195 - "1"
Cohesion: 0.67
Nodes (3): $type, $value, 1

### Community 196 - "3"
Cohesion: 0.67
Nodes (3): $type, $value, 3

### Community 197 - "8"
Cohesion: 0.67
Nodes (3): $type, $value, 8

### Community 198 - "destructive"
Cohesion: 0.67
Nodes (3): destructive, $type, $value

### Community 199 - "destructive-foreground"
Cohesion: 0.67
Nodes (3): destructive-foreground, $type, $value

### Community 200 - "muted"
Cohesion: 0.67
Nodes (3): muted, $type, $value

### Community 201 - "primary-foreground"
Cohesion: 0.67
Nodes (3): primary-foreground, $type, $value

### Community 202 - "ring"
Cohesion: 0.67
Nodes (3): ring, $type, $value

### Community 203 - "secondary-foreground"
Cohesion: 0.67
Nodes (3): secondary-foreground, $type, $value

### Community 242 - "brand.ts"
Cohesion: 0.42
Nodes (11): accentPreviewVars(), applyAccent(), contrast(), DEFAULT_ACCENT, initAccent(), luminance(), normalizeHex(), resetAccent() (+3 more)

### Community 244 - "_select_palette_for_mode"
Cohesion: 0.11
Nodes (14): _contrast_ratio(), _derive_dark_palette(), _palette_is_dark(), WCAG relative luminance of a #RRGGBB string, or None if unparseable., True when a colors.csv row's Background is a dark surface., WCAG contrast ratio for two hex colors, or None if either is invalid., Keep product brand tokens while deriving accessible dark surfaces., Pick the highest-ranked palette matching the resolved mode. Only the dark case… (+6 more)

## Knowledge Gaps
- **1106 isolated node(s):** `fs`, `path`, `fs`, `path`, `fs` (+1101 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1834 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **34 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `search()` connect `search` to `_normalize`, `DesignSystemGenerator`, `detect_domain`, `validate_data.py`, `test_text_layout_resilience.py`, `design_system.py`, `read_rows`, `scripts/core.py`, `_row_identities`, `BM25`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `DesignSystemGenerator` connect `DesignSystemGenerator` to `test_data_contracts.py`, `test_design_system_mode.py`, `_select_palette_for_mode`, `design_system.py`, `BM25`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Why does `Session` connect `Session` to `routers/plans.py`, `models.py`, `_build_smart_mesocycle`, `adapt_session_to_available_time`, `routers/users.py`, `routers/admin.py`, `routers/boxes.py`, `schemas/mesocycles.py`?**
  _High betweenness centrality (0.011) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `TailwindConfigGenerator` (e.g. with `TestGeneratedConfigIsValidJs` and `TestTailwindConfigGenerator`) actually correct?**
  _`TailwindConfigGenerator` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fs`, `path`, `fs` to the rest of the system?**
  _1106 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `AppShell.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.07164404223227752 - nodes in this community are weakly interconnected._
- **Should `ui.tsx` be split into smaller, more focused modules?**
  _Cohesion score 0.11279953243717125 - nodes in this community are weakly interconnected._