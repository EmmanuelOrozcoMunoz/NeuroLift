import streamlit as st
import requests
import extra_streamlit_components as stx
import datetime
import uuid

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="NeuroLift AI", page_icon="🧠", layout="wide")

# ==========================================
# GESTIÓN DE COOKIES Y SESIÓN (JWT)
# ==========================================
# Inicializamos el gestor de cookies directamente
cookie_manager = stx.CookieManager(key="Gestor_Cookies")

# 1. Leemos SOLO el Token encriptado de las cookies
jwt_token = cookie_manager.get(cookie="neurolift_jwt")

if "user_session" not in st.session_state:
    st.session_state.user_session = None

# True desde que el usuario cierra sesión explícitamente hasta que vuelve a loguearse.
# Bloquea la rehidratación automática mientras tanto: el borrado de la cookie es asíncrono
# (pasa por el componente JS de CookieManager) y podría no haberse completado todavía en el
# navegador aunque hayan pasado varios reruns (p. ej. mientras se llena el formulario de
# registro), así que no basta con saltar un solo rerun.
if "logged_out" not in st.session_state:
    st.session_state.logged_out = False

if "auth_view" not in st.session_state:
    st.session_state.auth_view = "login"

if "auth_message" not in st.session_state:
    st.session_state.auth_message = None

# ==========================================
# INTERCEPCIÓN GLOBAL DE 401 (sesión revocada/expirada)
# ==========================================
# Se parchea una sola vez por proceso (el módulo `requests` es un singleton que persiste
# entre reruns de Streamlit): cualquier llamada que haya llevado un header Authorization y
# reciba un 401 significa que el token ya no es válido en el servidor (expiró, cerraste
# sesión en otra pestaña, o un admin forzó la revocación). En vez de que cada una de las
# ~50 pantallas que llaman a la API muestre su propio error suelto, se regresa aquí mismo
# al login con un mensaje claro.
if not getattr(requests, "_neurolift_patched", False):
    _orig_get = requests.get
    _orig_post = requests.post
    _orig_put = requests.put
    _orig_delete = requests.delete

    def _check_revoked_session(response):
        if response.status_code == 401 and "Authorization" in response.request.headers:
            st.session_state.user_session = None
            st.session_state.logged_out = True
            st.session_state.auth_view = "login"
            st.session_state.auth_message = "Tu sesión expiró o fue cerrada en otro lugar. Inicia sesión de nuevo."
            cookie_manager.delete("neurolift_jwt", key=f"delete_jwt_401_{uuid.uuid4()}")
            st.rerun()
        return response

    def _patched_get(*a, **kw):
        return _check_revoked_session(_orig_get(*a, **kw))

    def _patched_post(*a, **kw):
        return _check_revoked_session(_orig_post(*a, **kw))

    def _patched_put(*a, **kw):
        return _check_revoked_session(_orig_put(*a, **kw))

    def _patched_delete(*a, **kw):
        return _check_revoked_session(_orig_delete(*a, **kw))

    requests.get = _patched_get
    requests.post = _patched_post
    requests.put = _patched_put
    requests.delete = _patched_delete
    requests._neurolift_patched = True

# Función auxiliar para enviar el token como un "Pase VIP"
def get_headers():
    if jwt_token:
        return {"Authorization": f"Bearer {jwt_token}"}
    return {}


def render_mesocycle_sessions(meso_id):
    """Trae el detalle completo de un mesociclo y renderiza sus sesiones, con edición inline.
    Reutilizable desde '🔍 Ver Rutinas' y desde '👨‍👩‍👧‍👦 Mis Grupos'."""
    res_detalle = requests.get(f"{API_URL}/mesocycles/{meso_id}", headers=get_headers())
    if res_detalle.status_code != 200:
        st.error("Error al cargar los detalles del mesociclo.")
        return

    datos = res_detalle.json()

    if not datos.get("sessions"):
        st.info("Este mesociclo todavía no tiene sesiones.")
        return

    dias_espanol = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    for sesion in datos.get("sessions", []):
        fecha_str = sesion.get("scheduled_date", "")
        nombre_dia = ""
        if fecha_str:
            try:
                fecha_obj = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
                nombre_dia = f"{dias_espanol[fecha_obj.weekday()]}, "
            except Exception:
                pass

        notas_atleta = sesion.get('athlete_notes', '')
        separador_notas = f" | {notas_atleta}" if notas_atleta else ""
        titulo_sesion = f"📅 {nombre_dia}{fecha_str}{separador_notas}"

        with st.expander(titulo_sesion):
            # --- FORMULARIO 1: EDITAR LO EXISTENTE (AGRUPADO E INTELIGENTE) ---
            with st.form(f"form_sesion_{sesion['id']}"):
                # 1. Agrupamos las series por nombre del ejercicio
                ejercicios_agrupados = {}
                for set_data in sesion.get("sets", []):
                    ej_nombre = set_data["exercise"]["name"]
                    if ej_nombre not in ejercicios_agrupados:
                        ejercicios_agrupados[ej_nombre] = {
                            "set_ids": [],
                            "reps": set_data.get("prescribed_reps") or 0,
                            "rpe": set_data.get("rpe") or 0,
                            "peso": set_data.get("prescribed_weight") or 0.0,
                        }
                    ejercicios_agrupados[ej_nombre]["set_ids"].append(set_data["id"])

                # Aquí guardaremos el "Plan de Acción" para cada ejercicio
                plan_de_accion = []

                st.markdown("##### 🏋️ Ejercicios Prescritos")

                for ej_nombre, datos_ej in ejercicios_agrupados.items():
                    col1, col2, col3, col4, col5 = st.columns([2.5, 1, 1, 1, 1.5])

                    original_ids = datos_ej["set_ids"]
                    first_id = original_ids[0]
                    num_series_originales = len(original_ids)

                    with col1:
                        nuevo_nombre = st.text_input("Ejercicio", value=ej_nombre, key=f"ex_{first_id}")
                    with col2:
                        nuevas_series = st.number_input("Series", value=num_series_originales, min_value=1, key=f"series_{first_id}")
                    with col3:
                        nuevas_reps = st.number_input("Reps", value=int(datos_ej["reps"]), key=f"reps_{first_id}")
                    with col4:
                        nuevo_rpe = st.number_input("RPE", value=int(datos_ej["rpe"]), min_value=0, max_value=10, step=1, key=f"rpe_{first_id}")
                    with col5:
                        nuevo_peso = st.number_input("Peso (kg)", value=float(datos_ej["peso"]), step=2.5, key=f"peso_{first_id}")

                    plan_de_accion.append({
                        "original_ids": original_ids,
                        "num_original": num_series_originales,
                        "num_nuevo": nuevas_series,
                        "session_id": sesion["id"],
                        "data": {
                            "exercise_name": nuevo_nombre,
                            "prescribed_reps": nuevas_reps,
                            "rpe": nuevo_rpe,
                            "prescribed_weight": nuevo_peso
                        }
                    })

                if st.form_submit_button("💾 Guardar Ajustes de esta Sesión"):
                    for plan in plan_de_accion:
                        limite_actualizar = min(plan["num_original"], plan["num_nuevo"])
                        for i in range(limite_actualizar):
                            requests.put(f"{API_URL}/sets/{plan['original_ids'][i]}", json=plan["data"], headers=get_headers())

                        if plan["num_nuevo"] < plan["num_original"]:
                            for i in range(plan["num_nuevo"], plan["num_original"]):
                                requests.delete(f"{API_URL}/sets/{plan['original_ids'][i]}", headers=get_headers())

                        elif plan["num_nuevo"] > plan["num_original"]:
                            series_a_crear = plan["num_nuevo"] - plan["num_original"]
                            for _ in range(series_a_crear):
                                requests.post(f"{API_URL}/sessions/{plan['session_id']}/sets/", json=plan["data"], headers=get_headers())

                    st.success("¡Ajustes y series guardados con éxito!")
                    st.rerun()

            st.markdown("---")

            # --- FORMULARIO 2: AÑADIR UN EJERCICIO NUEVO ---
            st.write("**➕ Añadir Ejercicio Extra**")
            with st.form(f"form_add_{sesion['id']}"):
                colA, colB, colC, colD, colE = st.columns([2.5, 1, 1, 1, 1.5])
                with colA:
                    nuevo_ej_nombre = st.text_input("Nombre del Ejercicio")
                with colB:
                    nuevo_ej_series = st.number_input("Series", min_value=1, value=3)
                with colC:
                    nuevo_ej_reps = st.number_input("Reps", min_value=1, value=10)
                with colD:
                    nuevo_ej_rpe = st.number_input("RPE", min_value=1, max_value=10, value=7, step=1)
                with colE:
                    nuevo_ej_peso = st.number_input("Peso (kg)", min_value=0.0, value=0.0, step=2.5)

                if st.form_submit_button("Añadir a la rutina"):
                    if nuevo_ej_nombre:
                        datos_nuevo = {
                            "exercise_name": nuevo_ej_nombre,
                            "prescribed_reps": nuevo_ej_reps,
                            "rpe": nuevo_ej_rpe,
                            "prescribed_weight": nuevo_ej_peso
                        }
                        for _ in range(nuevo_ej_series):
                            requests.post(f"{API_URL}/sessions/{sesion['id']}/sets/", json=datos_nuevo, headers=get_headers())
                        st.success(f"¡Ejercicio añadido con {nuevo_ej_series} series!")
                        st.rerun()
                    else:
                        st.warning("Debes escribir el nombre del ejercicio.")


def render_group_mesocycle_editor(grupo_id, programa, prog_key):
    """Editor de 'grupo completo': igual que el editor individual (ver ejercicios agrupados por
    fecha, editar series/reps/RPE/peso, quitar, añadir) pero cada cambio se aplica a TODOS los
    atletas del programa a la vez. Usa el mesociclo del primer atleta como plantilla de referencia
    para mostrar qué hay programado (todos comparten el mismo calendario)."""
    if not programa["athletes"]:
        st.info("Este programa no tiene atletas.")
        return

    ref_atleta = programa["athletes"][0]
    res_ref = requests.get(f"{API_URL}/mesocycles/{ref_atleta['mesocycle_id']}", headers=get_headers())
    if res_ref.status_code != 200:
        st.error("Error al cargar la plantilla del grupo.")
        return

    datos_ref = res_ref.json()
    st.caption(
        f"Vista de referencia: **{ref_atleta['full_name']}**. Los cambios aquí se aplican a todos los "
        "atletas del grupo que tengan ese ejercicio en esa fecha (cada quien conserva su propio peso, "
        "salvo que lo cambies explícitamente aquí)."
    )

    dias_espanol = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

    for sesion in datos_ref.get("sessions", []):
        fecha_str = sesion.get("scheduled_date", "")
        nombre_dia = ""
        if fecha_str:
            try:
                fecha_obj = datetime.datetime.strptime(fecha_str, "%Y-%m-%d")
                nombre_dia = f"{dias_espanol[fecha_obj.weekday()]}, "
            except Exception:
                pass

        with st.expander(f"📅 {nombre_dia}{fecha_str}"):
            # 1. Agrupamos las series por nombre del ejercicio (igual que en la vista individual)
            ejercicios_agrupados = {}
            for set_data in sesion.get("sets", []):
                ej_nombre = set_data["exercise"]["name"]
                if ej_nombre not in ejercicios_agrupados:
                    ejercicios_agrupados[ej_nombre] = {
                        "reps": set_data.get("prescribed_reps") or 0,
                        "rpe": set_data.get("rpe") or 0,
                        "peso": set_data.get("prescribed_weight") or 0.0,
                        "series": 0,
                    }
                ejercicios_agrupados[ej_nombre]["series"] += 1

            if ejercicios_agrupados:
                with st.form(f"form_group_edit_{prog_key}_{fecha_str}"):
                    st.markdown("##### 🏋️ Ejercicios prescritos (aplica a todo el grupo)")
                    plan_grupo = []
                    for ej_nombre, datos_ej in ejercicios_agrupados.items():
                        col1, col2, col3, col4, col5 = st.columns([2.5, 1, 1, 1, 1.5])
                        with col1:
                            nuevo_nombre = st.text_input("Ejercicio", value=ej_nombre, key=f"grp_ex_{prog_key}_{fecha_str}_{ej_nombre}")
                        with col2:
                            nuevas_series = st.number_input("Series", value=datos_ej["series"], min_value=1, key=f"grp_series_{prog_key}_{fecha_str}_{ej_nombre}")
                        with col3:
                            nuevas_reps = st.number_input("Reps", value=int(datos_ej["reps"]), key=f"grp_reps_{prog_key}_{fecha_str}_{ej_nombre}")
                        with col4:
                            nuevo_rpe = st.number_input("RPE", value=int(datos_ej["rpe"]), min_value=0, max_value=10, step=1, key=f"grp_rpe_{prog_key}_{fecha_str}_{ej_nombre}")
                        with col5:
                            nuevo_peso = st.number_input("Peso (kg)", value=float(datos_ej["peso"]), step=2.5, key=f"grp_peso_{prog_key}_{fecha_str}_{ej_nombre}")

                        plan_grupo.append({
                            "exercise_name": ej_nombre,
                            "new_exercise_name": nuevo_nombre,
                            "prescribed_sets": nuevas_series,
                            "prescribed_reps": nuevas_reps,
                            "rpe": nuevo_rpe,
                            "prescribed_weight": nuevo_peso,
                        })

                    if st.form_submit_button("💾 Guardar cambios para TODO el grupo"):
                        for plan in plan_grupo:
                            payload = {
                                "program_name": programa["name"],
                                "program_start_date": programa["start_date"],
                                "scheduled_date": fecha_str,
                                **plan,
                            }
                            requests.put(
                                f"{API_URL}/groups/{grupo_id}/sessions/bulk-update-exercise",
                                json=payload, headers=get_headers()
                            )
                        st.success("¡Cambios aplicados a todo el grupo!")
                        st.rerun()

                st.markdown("**🗑️ Quitar un ejercicio de todo el grupo**")
                cold1, cold2 = st.columns([3, 1])
                with cold1:
                    ejercicio_a_borrar = st.selectbox(
                        "Ejercicio a eliminar", options=list(ejercicios_agrupados.keys()),
                        key=f"grp_del_select_{prog_key}_{fecha_str}"
                    )
                with cold2:
                    st.write("")
                    if st.button("Eliminar", key=f"grp_del_btn_{prog_key}_{fecha_str}"):
                        payload_del = {
                            "program_name": programa["name"],
                            "program_start_date": programa["start_date"],
                            "scheduled_date": fecha_str,
                            "exercise_name": ejercicio_a_borrar,
                        }
                        requests.post(
                            f"{API_URL}/groups/{grupo_id}/sessions/bulk-delete-exercise",
                            json=payload_del, headers=get_headers()
                        )
                        st.success(f"'{ejercicio_a_borrar}' eliminado de todo el grupo.")
                        st.rerun()
            else:
                st.info("Todavía no hay ejercicios en esta fecha.")

            st.markdown("---")
            st.write("**➕ Añadir ejercicio nuevo para TODO el grupo**")
            with st.form(f"form_group_add_{prog_key}_{fecha_str}"):
                cb1, cb2, cb3, cb4, cb5 = st.columns([2.5, 1, 1, 1, 1.5])
                with cb1:
                    ej_nombre_bulk = st.text_input("Ejercicio", key=f"bulk_ex_{prog_key}_{fecha_str}")
                with cb2:
                    ej_series_bulk = st.number_input("Series", min_value=1, value=3, key=f"bulk_series_{prog_key}_{fecha_str}")
                with cb3:
                    ej_reps_bulk = st.number_input("Reps", min_value=1, value=8, key=f"bulk_reps_{prog_key}_{fecha_str}")
                with cb4:
                    ej_rpe_bulk = st.number_input("RPE", min_value=1, max_value=10, value=7, key=f"bulk_rpe_{prog_key}_{fecha_str}")
                with cb5:
                    ej_peso_bulk = st.number_input("Peso (kg)", min_value=0.0, value=0.0, step=2.5, key=f"bulk_peso_{prog_key}_{fecha_str}")

                if st.form_submit_button("➕ Añadir a TODO el grupo"):
                    if ej_nombre_bulk:
                        payload_bulk = {
                            "program_name": programa["name"],
                            "program_start_date": programa["start_date"],
                            "scheduled_date": fecha_str,
                            "exercise_name": ej_nombre_bulk,
                            "prescribed_sets": ej_series_bulk,
                            "prescribed_reps": ej_reps_bulk,
                            "rpe": ej_rpe_bulk,
                            "prescribed_weight": ej_peso_bulk
                        }
                        res_bulk = requests.post(
                            f"{API_URL}/groups/{grupo_id}/sessions/bulk-add-exercise",
                            json=payload_bulk, headers=get_headers()
                        )
                        if res_bulk.status_code == 200:
                            st.success(res_bulk.json().get("message"))
                            st.rerun()
                        else:
                            st.error(f"Error: {res_bulk.text}")
                    else:
                        st.warning("Escribe el nombre del ejercicio.")


def render_group_programs(grupo_id):
    """Lista los mesociclos programados para un grupo y, para cada uno, una pestaña 'Grupo
    completo' (edición masiva) más una pestaña por cada atleta (edición individual).
    Reutilizable desde '👨‍👩‍👧‍👦 Mis Grupos' y desde '🔍 Ver Rutinas'."""
    st.markdown("##### 🏋️ Mesociclos programados para este grupo")
    res_meso_grupo = requests.get(f"{API_URL}/groups/{grupo_id}/mesocycles", headers=get_headers())
    if res_meso_grupo.status_code == 200 and res_meso_grupo.json():
        for programa in res_meso_grupo.json():
            estado = "🟢 Activo" if any(a["is_active"] for a in programa["athletes"]) else "⚪ Finalizado"
            st.write(
                f"**{programa['name']}** — {programa['discipline']} "
                f"({programa['start_date']} → {programa.get('end_date') or '?'}) · {estado}"
            )

            prog_key = f"{grupo_id}_{programa['name']}_{programa['start_date']}"
            nombres_tabs = ["👥 Grupo completo"] + [a["full_name"] for a in programa["athletes"]]
            tabs_programa = st.tabs(nombres_tabs)

            # --- TAB 0: EDITAR EL MESOCICLO DE TODO EL GRUPO A LA VEZ ---
            with tabs_programa[0]:
                render_group_mesocycle_editor(grupo_id, programa, prog_key)

            # --- TABS SIGUIENTES: EDITAR INDIVIDUALMENTE A CADA ATLETA ---
            for tab_atleta, a in zip(tabs_programa[1:], programa["athletes"]):
                with tab_atleta:
                    render_mesocycle_sessions(a["mesocycle_id"])
    else:
        st.info("Todavía no hay ningún mesociclo programado para este grupo.")


def render_athlete_session(sesion):
    """Muestra las series prescritas de una sesión y deja que el ATLETA registre lo que
    realmente hizo (reps/peso reales por serie), y marque la sesión como completada."""
    sets = sesion.get("sets", [])
    if not sets:
        st.info("Esta sesión todavía no tiene ejercicios asignados por tu coach.")
        return

    if sesion.get("athlete_notes"):
        st.caption(f"📝 {sesion['athlete_notes']}")

    if sesion.get("status") == "completed":
        st.caption("✅ Ya marcaste esta sesión como completada. Puedes actualizar tus registros si quieres.")

    with st.form(f"form_log_{sesion['id']}"):
        plan_log = []
        ejercicio_actual = None
        contador_serie = 0

        for set_data in sets:
            nombre_ej = set_data["exercise"]["name"]
            if nombre_ej != ejercicio_actual:
                st.markdown(f"**🏋️ {nombre_ej}**")
                ejercicio_actual = nombre_ej
                contador_serie = 0
            contador_serie += 1

            prescrito = f"Prescrito: {set_data['prescribed_reps']} reps"
            if set_data.get("prescribed_weight"):
                prescrito += f" @ {set_data['prescribed_weight']}kg"
            if set_data.get("rpe") is not None:
                prescrito += f" (RPE {set_data['rpe']})"

            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"Serie {contador_serie} — {prescrito}")
            with col2:
                reps_reales = st.number_input(
                    "Reps reales", min_value=0, max_value=200,
                    value=int(set_data.get("actual_reps") or set_data.get("prescribed_reps") or 0),
                    key=f"actual_reps_{set_data['id']}"
                )
            with col3:
                peso_real = st.number_input(
                    "Peso real (kg)", min_value=0.0, step=2.5,
                    value=float(set_data.get("actual_weight") or set_data.get("prescribed_weight") or 0.0),
                    key=f"actual_weight_{set_data['id']}"
                )

            plan_log.append({"set_id": set_data["id"], "actual_reps": reps_reales, "actual_weight": peso_real})

        if st.form_submit_button("✅ Guardar entrenamiento"):
            for item in plan_log:
                requests.put(
                    f"{API_URL}/sets/{item['set_id']}/log",
                    json={"actual_reps": item["actual_reps"], "actual_weight": item["actual_weight"]},
                    headers=get_headers()
                )
            requests.post(f"{API_URL}/sessions/{sesion['id']}/complete", headers=get_headers())
            st.success("¡Entrenamiento guardado! Buen trabajo 💪")
            st.rerun()


def render_athlete_session_with_adapt(sesion_original, sesion_adaptada):
    """Envuelve render_athlete_session con la opción de pedir/ver una versión adaptada al
    tiempo disponible. La sesión original nunca se modifica; la adaptada es una sesión aparte
    para el mismo día que el atleta puede ver junto a la normal y elegir cuál seguir."""
    if sesion_adaptada:
        vista = st.radio(
            "¿Cuál versión quieres ver?",
            ["📋 Normal", f"⏱️ Adaptada ({sesion_adaptada.get('duration_minutes', '?')} min)"],
            horizontal=True, key=f"vista_{sesion_original['id']}"
        )
        if vista.startswith("⏱️"):
            render_athlete_session(sesion_adaptada)
        else:
            render_athlete_session(sesion_original)
    else:
        render_athlete_session(sesion_original)

    with st.expander("⏱️ ¿Tienes menos tiempo hoy?"):
        st.caption("Genera una versión más corta de esta sesión sin perder la original — podrás elegir cuál seguir.")
        with st.form(f"form_adapt_{sesion_original['id']}"):
            minutos = st.number_input(
                "Minutos disponibles", min_value=10, max_value=180,
                value=sesion_adaptada.get("duration_minutes", 60) if sesion_adaptada else 60, step=5
            )
            if st.form_submit_button("🧠 Adaptar sesión"):
                with st.spinner("Adaptando tu sesión..."):
                    res_adapt = requests.post(
                        f"{API_URL}/sessions/{sesion_original['id']}/adapt",
                        json={"available_minutes": minutos}, headers=get_headers()
                    )
                if res_adapt.status_code == 200:
                    st.success(f"¡Lista! Ya tienes una versión de {minutos} min para esta sesión.")
                    st.rerun()
                else:
                    st.error(f"Error al adaptar la sesión: {res_adapt.text}")


# 2. HIDRATACIÓN: Si hay token en la cookie, pero Streamlit olvidó quién eres, le preguntamos al backend
# (no se intenta mientras "logged_out" esté activo: el usuario cerró sesión explícitamente y no
# queremos revivirla solo porque la cookie tarde en borrarse del navegador)
if not st.session_state.logged_out and jwt_token and st.session_state.user_session is None:
    # Usamos la nueva ruta /auth/me enviando el token en las cabeceras
    res_me = requests.get(f"{API_URL}/auth/me", headers=get_headers())
    if res_me.status_code == 200:
        st.session_state.user_session = res_me.json()
    else:
        # Si el token expiró o es falso, lo destruimos
        cookie_manager.delete("neurolift_jwt", key=f"delete_invalid_{uuid.uuid4()}")
        st.session_state.user_session = None

# ==========================================
# PANTALLA DE LOGIN / REGISTRO
# ==========================================
if st.session_state.user_session is None:
    st.title("Bienvenido a NeuroLift 🧠")
    st.subheader("La plataforma inteligente de entrenamiento")

    # Botones en vez de st.tabs: así podemos forzar el cambio a "login" por código
    # (p. ej. justo después de un registro exitoso), algo que st.tabs no permite.
    col_tab1, col_tab2 = st.columns(2)
    with col_tab1:
        if st.button(
            "🔑 Iniciar Sesión", use_container_width=True,
            type="primary" if st.session_state.auth_view == "login" else "secondary"
        ):
            st.session_state.auth_view = "login"
            st.rerun()
    with col_tab2:
        if st.button(
            "📝 Crear Cuenta", use_container_width=True,
            type="primary" if st.session_state.auth_view == "register" else "secondary"
        ):
            st.session_state.auth_view = "register"
            st.rerun()

    if st.session_state.auth_message:
        st.success(st.session_state.auth_message)
        st.session_state.auth_message = None

    if st.session_state.auth_view == "login":
        with st.form("form_login"):
            log_email = st.text_input("Correo electrónico")
            log_pass = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                res = requests.post(f"{API_URL}/auth/login", json={"email": log_email, "password": log_pass})

                if res.status_code == 200:
                    datos_token = res.json()
                    token = datos_token["access_token"]

                    # 1. Guardamos el TOKEN en la cookie para el futuro
                    cookie_manager.set("neurolift_jwt", token, key=f"set_jwt_login_{uuid.uuid4()}")

                    # 2. Vamos de inmediato al backend a traer tus datos reales ("Hidratación" manual)
                    res_me = requests.get(f"{API_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})

                    if res_me.status_code == 200:
                        # 3. Te metemos al sistema manualmente
                        st.session_state.user_session = res_me.json()
                        st.session_state.logged_out = False
                        st.success("¡Autenticación exitosa! Entrando...")
                        st.rerun()
                    else:
                        st.error("Error al obtener el perfil de usuario.")
                else:
                    st.error("Credenciales incorrectas")

    else:
        with st.form("form_registro"):
            reg_name = st.text_input("Nombre completo")
            reg_email = st.text_input("Correo electrónico")
            reg_pass = st.text_input("Contraseña", type="password")
            reg_rol = st.selectbox("¿Cuál es tu rol?", ["athlete", "coach"], format_func=lambda x: "Atleta" if x == "athlete" else "Entrenador (Coach)")

            if st.form_submit_button("Crear Cuenta"):
                datos = {
                    "full_name": reg_name,
                    "email": reg_email,
                    "password": reg_pass,
                    "role": reg_rol
                }
                res = requests.post(f"{API_URL}/auth/register", json=datos)
                if res.status_code == 200:
                    st.session_state.auth_view = "login"
                    # Mensaje genérico del backend: no revela si el correo ya estaba
                    # registrado o no (evita que alguien use este formulario para enumerar cuentas).
                    st.session_state.auth_message = res.json().get("message", "Listo. Inicia sesión con tu correo y contraseña.")
                    st.rerun()
                else:
                    try:
                        st.error(res.json().get("detail", "Error al crear la cuenta"))
                    except:
                        st.error(f"Error crítico: {res.text}")

# ==========================================
# APLICACIÓN PRINCIPAL (USUARIO LOGUEADO)
# ==========================================
else:
    usuario_actual = st.session_state.user_session
    
   # Barra lateral unificada
    with st.sidebar:
        st.write(f"👤 **{usuario_actual['full_name']}**")
        etiquetas_rol = {"coach": "Coach", "athlete": "Atleta", "admin": "Administrador"}
        st.write(f"🏷️ Rol: {etiquetas_rol.get(usuario_actual.get('role'), usuario_actual.get('role'))}")
        
        if st.button("Cerrar Sesión"):
            # Revocación real del lado del servidor (no solo borrar la cookie local): invalida
            # este token y cualquier otro que este usuario tuviera en otros dispositivos.
            requests.post(f"{API_URL}/auth/logout", headers=get_headers())
            st.session_state.user_session = None
            st.session_state.logged_out = True
            st.session_state.auth_view = "login"
            cookie_manager.delete("neurolift_jwt", key=f"delete_jwt_logout_{uuid.uuid4()}")
            st.rerun()
            
        st.markdown("---")
        
    # RUTEO SEGÚN EL ROL
    if usuario_actual["role"] == "coach":
        # ==========================================
        # INTERFAZ DEL COACH
        # ==========================================
        st.title("Panel de Control - Coach 📊")
        
        # Aquí pegas el menú lateral que ya tenías para el coach:
        st.sidebar.header("Menú del Entrenador")
        opcion = st.sidebar.radio(
            "Navegación",
            ["👥 Nuevo Atleta", "👨‍👩‍👧‍👦 Mis Grupos", "⚙️ Crear Mesociclo con IA", "✍️ Crear Mesociclo Manual", "🔍 Ver Rutinas", "💪 Toma de Marcas (PRs)"]
        )
        
       # ==========================================
        # SECCIÓN: NUEVO ATLETA
        # ==========================================
        if opcion == "👥 Nuevo Atleta":
            st.subheader("👥 Registrar Nuevo Atleta")
            st.caption("Se crea una cuenta con una contraseña temporal; compártela con el atleta para que inicie sesión.")
            with st.form("form_nuevo_atleta"):
                nombre = st.text_input("Nombre completo")
                correo = st.text_input("Correo electrónico")
                temp_pass = st.text_input("Contraseña temporal", type="password")
                peso = st.number_input("Peso corporal (kg)", min_value=0.0, step=0.5, value=70.0)

                submit_btn = st.form_submit_button("Registrar Atleta")

                if submit_btn and nombre and correo and temp_pass:
                    datos_atleta = {
                        "full_name": nombre,
                        "email": correo,
                        "password": temp_pass,
                        "role": "athlete",
                        "body_weight": peso
                    }
                    res = requests.post(f"{API_URL}/auth/register", json=datos_atleta)

                    if res.status_code == 200:
                        # Respuesta genérica a propósito: si el correo ya tenía cuenta, no se
                        # sobrescribió nada y este mensaje no lo distingue (evita enumeración).
                        # Si el atleta no puede iniciar sesión después, probablemente ya existía
                        # con otra contraseña.
                        st.success(res.json().get("message", f"Solicitud procesada para {nombre}."))
                    else:
                        st.error(f"Error del servidor: {res.text}")
                elif submit_btn:
                    st.warning("Nombre, correo y contraseña temporal son obligatorios.")

        # ==========================================
        # SECCIÓN: MIS GRUPOS
        # ==========================================
        elif opcion == "👨‍👩‍👧‍👦 Mis Grupos":
            st.subheader("👨‍👩‍👧‍👦 Mis Grupos de Atletas")
            st.caption("Organiza a tus atletas en grupos para programarles mesociclos a todos a la vez.")

            res_atletas_g = requests.get(f"{API_URL}/users/athletes", headers=get_headers())
            atletas_disponibles = res_atletas_g.json() if res_atletas_g.status_code == 200 else []
            mapa_atletas = {a["id"]: a["full_name"] for a in atletas_disponibles}

            with st.expander("➕ Crear nuevo grupo"):
                with st.form("form_nuevo_grupo"):
                    nombre_grupo = st.text_input("Nombre del grupo (ej. 'Bloque Fuerza A')")
                    miembros_iniciales = st.multiselect(
                        "Atletas a incluir (opcional, puedes añadir más después)",
                        options=list(mapa_atletas.keys()),
                        format_func=lambda x: mapa_atletas.get(x, x)
                    )
                    if st.form_submit_button("Crear Grupo"):
                        if not nombre_grupo:
                            st.error("Debes darle un nombre al grupo.")
                        else:
                            res_g = requests.post(
                                f"{API_URL}/groups/",
                                json={"name": nombre_grupo, "athlete_ids": miembros_iniciales},
                                headers=get_headers()
                            )
                            if res_g.status_code == 200:
                                st.success(f"¡Grupo '{nombre_grupo}' creado con éxito!")
                                st.rerun()
                            else:
                                st.error(f"Error al crear el grupo: {res_g.text}")

            st.markdown("---")
            st.markdown("### 📋 Mis grupos actuales")

            res_grupos = requests.get(f"{API_URL}/groups/", headers=get_headers())
            if res_grupos.status_code == 200 and res_grupos.json():
                for grupo in res_grupos.json():
                    with st.expander(f"👥 {grupo['name']} ({grupo['member_count']} atleta(s))"):
                        res_detalle_g = requests.get(f"{API_URL}/groups/{grupo['id']}", headers=get_headers())
                        if res_detalle_g.status_code == 200:
                            detalle = res_detalle_g.json()
                            miembros_actuales = detalle.get("members", [])

                            if miembros_actuales:
                                for m in miembros_actuales:
                                    colm1, colm2 = st.columns([4, 1])
                                    with colm1:
                                        st.write(f"🔹 {m['full_name']} ({m['email']})")
                                    with colm2:
                                        if st.button("Quitar", key=f"quitar_{grupo['id']}_{m['id']}"):
                                            requests.delete(
                                                f"{API_URL}/groups/{grupo['id']}/members/{m['id']}",
                                                headers=get_headers()
                                            )
                                            st.rerun()
                            else:
                                st.info("Este grupo todavía no tiene atletas.")

                            render_group_programs(grupo["id"])

                            st.markdown("---")

                            ids_actuales = {m["id"] for m in miembros_actuales}
                            opciones_para_agregar = {
                                aid: nombre for aid, nombre in mapa_atletas.items() if aid not in ids_actuales
                            }
                            if opciones_para_agregar:
                                with st.form(f"form_agregar_{grupo['id']}"):
                                    nuevos_miembros = st.multiselect(
                                        "Añadir atletas a este grupo",
                                        options=list(opciones_para_agregar.keys()),
                                        format_func=lambda x: opciones_para_agregar[x]
                                    )
                                    if st.form_submit_button("Añadir seleccionados"):
                                        if nuevos_miembros:
                                            requests.post(
                                                f"{API_URL}/groups/{grupo['id']}/members",
                                                json={"athlete_ids": nuevos_miembros},
                                                headers=get_headers()
                                            )
                                            st.rerun()

                            if st.button("🗑️ Eliminar grupo", key=f"eliminar_{grupo['id']}"):
                                requests.delete(f"{API_URL}/groups/{grupo['id']}", headers=get_headers())
                                st.rerun()
            else:
                st.info("Aún no tienes grupos creados. Crea el primero arriba.")

        # ==========================================
        # SECCIÓN: CREAR MESOCICLO
        # ==========================================
        elif opcion == "⚙️ Crear Mesociclo con IA":
            st.subheader("🤖 Generar Mesociclo con IA")
            st.markdown("Diseña la estructura y deja que Gemini calcule los volúmenes, ejercicios y porcentajes.")

            destino = st.radio("Aplicar a:", ["Un atleta", "Un grupo completo"], horizontal=True, key="destino_ia")

            atleta_seleccionado = None
            grupo_seleccionado = None

            if destino == "Un atleta":
                res_atletas = requests.get(f"{API_URL}/users/athletes", headers=get_headers())
                opciones_atletas = {a["id"]: a["full_name"] for a in res_atletas.json()} if res_atletas.status_code == 200 else {}
                if opciones_atletas:
                    atleta_seleccionado = st.selectbox(
                        "Seleccionar Atleta",
                        options=list(opciones_atletas.keys()),
                        format_func=lambda x: opciones_atletas[x]
                    )
                else:
                    st.warning("Primero debes registrar un atleta en la pestaña 'Nuevo Atleta'.")
            else:
                res_grupos = requests.get(f"{API_URL}/groups/", headers=get_headers())
                opciones_grupos = {g["id"]: f"{g['name']} ({g['member_count']} atletas)" for g in res_grupos.json()} if res_grupos.status_code == 200 else {}
                if opciones_grupos:
                    grupo_seleccionado = st.selectbox(
                        "Seleccionar Grupo",
                        options=list(opciones_grupos.keys()),
                        format_func=lambda x: opciones_grupos[x]
                    )
                else:
                    st.warning("Primero crea un grupo en la pestaña '👨‍👩‍👧‍👦 Mis Grupos'.")

            if atleta_seleccionado or grupo_seleccionado:
                with st.form("form_ia_meso"):
                    nombre_meso = st.text_input("Nombre de la Rutina", value="Bloque de Fuerza 1")
                    disciplina = st.selectbox("Disciplina", ["Powerbuilding", "Powerlifting", "Hipertrofia", "Weightlifting"])

                    # El campo libre donde el coach da sus notas
                    objetivo = st.text_area(
                        "Objetivo y Contexto (Opcional pero recomendado)",
                        placeholder="Ej. Priorizar sentadilla, tiene dolor leve en hombro derecho, enfocar accesorios en espalda..."
                    )

                    fecha_inicio = st.date_input("Fecha de Inicio")

                    col1, col2 = st.columns(2)
                    with col1:
                        semanas = st.number_input("Semanas de duración", min_value=1, max_value=12, value=4)

                    with col2:
                        mapa_dias = {
                            "Lunes": 0, "Martes": 1, "Miércoles": 2,
                            "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6
                        }
                        dias_elegidos = st.multiselect(
                            "Días de entrenamiento",
                            options=list(mapa_dias.keys()),
                            default=["Lunes", "Miércoles", "Viernes"]
                        )

                    duracion_sesion = st.number_input(
                        "⏱️ Duración objetivo por sesión (min)",
                        min_value=0, max_value=180, value=60, step=5,
                        help="La IA ajustará el volumen de cada sesión para que quepa en este tiempo. Déjalo en 0 para no restringir."
                    )

                    if st.form_submit_button("✨ Generar con Inteligencia Artificial"):
                            if not nombre_meso:
                                st.error("Debes darle un nombre al mesociclo.")
                            elif not dias_elegidos:
                                st.error("Selecciona al menos un día de entrenamiento.")
                            else:
                                numeros_dias = [mapa_dias[dia] for dia in dias_elegidos]
                                contexto = objetivo if objetivo else "Progreso lineal y mejora técnica general."

                                if grupo_seleccionado:
                                    datos_ia = {
                                        "group_id": grupo_seleccionado,
                                        "name": nombre_meso,
                                        "discipline": disciplina,
                                        "start_date": str(fecha_inicio),
                                        "weeks_count": semanas,
                                        "training_days": numeros_dias,
                                        "context": contexto,
                                        "session_duration_minutes": duracion_sesion if duracion_sesion > 0 else None
                                    }
                                    with st.spinner("🧠 Generando mesociclo para todo el grupo (esto puede tomar un momento por cada atleta)..."):
                                        res_ia = requests.post(f"{API_URL}/ai/generate-smart-mesocycle/group", json=datos_ia, headers=get_headers())
                                        if res_ia.status_code == 200:
                                            st.success(res_ia.json().get("message", "¡Mesociclo grupal generado!"))
                                            st.info("Ve a '🔍 Ver Rutinas' para revisar los pesos calculados de cada atleta.")
                                        else:
                                            st.error(f"Hubo un error con la IA: {res_ia.text}")
                                else:
                                    datos_ia = {
                                        "user_id": atleta_seleccionado,
                                        "name": nombre_meso,
                                        "discipline": disciplina,
                                        "start_date": str(fecha_inicio),
                                        "weeks_count": semanas,
                                        "training_days": numeros_dias,
                                        "context": contexto,
                                        "session_duration_minutes": duracion_sesion if duracion_sesion > 0 else None
                                    }
                                    with st.spinner("🧠 Gemini Lite está procesando el contexto y calculando pesos (RAG)..."):
                                        res_ia = requests.post(f"{API_URL}/ai/generate-smart-mesocycle/", json=datos_ia, headers=get_headers())
                                        if res_ia.status_code == 200:
                                            st.success("¡Mesociclo estructurado con IA creado con éxito!")
                                            st.info("Ve a '🔍 Ver Rutinas' para revisar los pesos calculados.")
                                        else:
                                            st.error(f"Hubo un error con la IA: {res_ia.text}")
        # ==========================================
        # SECCIÓN: VER RUTINAS (Lo que ya tenías)
        # ==========================================
        # ==========================================
        # SECCIÓN: VER Y EDITAR RUTINAS
        # ==========================================
        # ==========================================
        # SECCIÓN: VER Y EDITAR RUTINAS
        # ==========================================
        elif opcion == "🔍 Ver Rutinas":
            st.subheader("🔍 Gestión y Edición de Mesociclos")
            st.caption(
                "Solo para atletas sueltos (sin grupo). Si un atleta pertenece a un grupo, "
                "consulta y edita su rutina desde '👨‍👩‍👧‍👦 Mis Grupos'."
            )

            # Atletas que ya pertenecen a algún grupo: su rutina se ve desde "Mis Grupos", no aquí
            res_grupos_vr = requests.get(f"{API_URL}/groups/", headers=get_headers())
            grupos_vr = res_grupos_vr.json() if res_grupos_vr.status_code == 200 else []

            ids_agrupados = set()
            for g in grupos_vr:
                res_det_g = requests.get(f"{API_URL}/groups/{g['id']}", headers=get_headers())
                if res_det_g.status_code == 200:
                    ids_agrupados.update(m["id"] for m in res_det_g.json().get("members", []))

            res_usuarios = requests.get(f"{API_URL}/users/athletes", headers=get_headers())
            if res_usuarios.status_code == 200 and len(res_usuarios.json()) > 0:
                usuarios = res_usuarios.json()
                opciones_usuarios = {u['full_name']: u['id'] for u in usuarios if u['id'] not in ids_agrupados}

                if not opciones_usuarios:
                    st.info("Todos tus atletas ya están en algún grupo. Consulta sus rutinas desde '👨‍👩‍👧‍👦 Mis Grupos'.")
                else:
                    atleta_seleccionado = st.selectbox("1. Selecciona al Atleta:", list(opciones_usuarios.keys()))
                    user_id = opciones_usuarios[atleta_seleccionado]

                    # 2. Buscamos los mesociclos SOLO de ese atleta
                    res_meso = requests.get(f"{API_URL}/users/{user_id}/mesocycles/", headers=get_headers())
                    if res_meso.status_code == 200 and len(res_meso.json()) > 0:
                        mesociclos = res_meso.json()
                        opciones_meso = {f"🏋️ {m.get('name', 'Rutina')} - {m['discipline']} ({m['start_date']})": m['id'] for m in mesociclos}

                        meso_seleccionado = st.selectbox("2. Selecciona el Mesociclo:", list(opciones_meso.keys()))
                        meso_id = opciones_meso[meso_seleccionado]

                        st.markdown("---")

                        render_mesocycle_sessions(meso_id)
                    else:
                        st.info("Este atleta aún no tiene mesociclos generados.")
            else:
                st.warning("Primero debes registrar un atleta en la pestaña 'Nuevo Atleta'.")

        # ==========================================
        # SECCIÓN: TOMA DE MARCAS (RMs)
        # ==========================================
        elif opcion == "💪 Toma de Marcas (PRs)":
            st.subheader("💪 Toma de Marcas y Perfil de Fuerza")

            res_usuarios = requests.get(f"{API_URL}/users/athletes", headers=get_headers())

            if res_usuarios.status_code == 200 and len(res_usuarios.json()) > 0:
                usuarios = res_usuarios.json()
                opciones_usuarios = {u['full_name']: u['id'] for u in usuarios}

                atleta_seleccionado = st.selectbox("Selecciona al Atleta:", list(opciones_usuarios.keys()))
                user_id = opciones_usuarios[atleta_seleccionado]

                st.markdown("---")

                # ==========================================
                # NUEVO: MOSTRAR LAS MARCAS ACTUALES
                # ==========================================
                st.markdown(f"### 📊 Perfil de Fuerza de {atleta_seleccionado}")
                res_prs = requests.get(f"{API_URL}/users/{user_id}/records/", headers=get_headers())
                
                if res_prs.status_code == 200:
                    marcas = res_prs.json()
                    if marcas:
                        # Dibujamos columnas dinámicas para que se vea como un Dashboard
                        cols = st.columns(4) 
                        for i, marca in enumerate(marcas):
                            with cols[i % 4]: # Reparte las tarjetas en filas de 4
                                # Formateamos la fecha para que se vea bonita (YYYY-MM-DD)
                                fecha = marca['last_updated'].split("T")[0]
                                st.metric(
                                    label=marca['exercise_name'], 
                                    value=f"{marca['max_weight_kg']} kg",
                                    delta=f"Último test: {fecha}",
                                    delta_color="off"
                                )
                    else:
                        st.info("Este atleta aún no tiene marcas registradas. ¡Haz su primera toma de marcas abajo!")
                else:
                    st.error("Error al cargar el historial de marcas.")
                    
                st.markdown("---")
                # ==========================================
                
                # Aquí sigue el formulario que ya tenías para registrar un nuevo PR
                st.write(f"**Registrar nueva marca**")
                with st.form("form_nuevo_pr"):
                    col1, col2 = st.columns(2)
                    with col1:
                        ejercicio = st.text_input("Ejercicio (Ej: Back Squat, Snatch)")
                    with col2:
                        peso = st.number_input("1RM en kg", min_value=0.0, step=2.5)
                        
                    submit_pr = st.form_submit_button("Guardar Marca")
                    
                    if submit_pr and ejercicio:
                        datos_pr = {"exercise_name": ejercicio, "max_weight_kg": peso}
                        res_pr = requests.post(f"{API_URL}/users/{user_id}/records/", json=datos_pr, headers=get_headers())
                        
                        if res_pr.status_code == 200:
                            st.success(f"¡Marca de {ejercicio} actualizada a {peso}kg!")
                            # Un pequeño truco para recargar la página y ver el nuevo PR al instante
                            st.rerun() 
                        else:
                            st.error("Error al guardar la marca.")
        elif opcion == "✍️ Crear Mesociclo Manual":
            st.subheader("✍️ Creación Manual de Mesociclo")
            st.markdown("Genera el esqueleto de tu mesociclo y llénalo de ejercicios en la pestaña **🔍 Ver Rutinas**.")

            destino_manual = st.radio("Aplicar a:", ["Un atleta", "Un grupo completo"], horizontal=True, key="destino_manual")

            atleta_seleccionado = None
            grupo_seleccionado = None

            if destino_manual == "Un atleta":
                res_atletas = requests.get(f"{API_URL}/users/athletes", headers=get_headers())
                opciones_atletas = {a["id"]: a["full_name"] for a in res_atletas.json()} if res_atletas.status_code == 200 else {}
                if opciones_atletas:
                    atleta_seleccionado = st.selectbox(
                        "Seleccionar Atleta",
                        options=list(opciones_atletas.keys()),
                        format_func=lambda x: opciones_atletas[x]
                    )
                else:
                    st.warning("No tienes atletas registrados. Pide a tus clientes que creen su cuenta como 'Atleta'.")
            else:
                res_grupos = requests.get(f"{API_URL}/groups/", headers=get_headers())
                opciones_grupos = {g["id"]: f"{g['name']} ({g['member_count']} atletas)" for g in res_grupos.json()} if res_grupos.status_code == 200 else {}
                if opciones_grupos:
                    grupo_seleccionado = st.selectbox(
                        "Seleccionar Grupo",
                        options=list(opciones_grupos.keys()),
                        format_func=lambda x: opciones_grupos[x]
                    )
                else:
                    st.warning("Primero crea un grupo en la pestaña '👨‍👩‍👧‍👦 Mis Grupos'.")

            if atleta_seleccionado or grupo_seleccionado:
                with st.form("form_manual_meso"):
                    nombre_meso = st.text_input("Nombre de la Rutina (ej. Fase de Fuerza)")
                    disciplina = st.selectbox("Disciplina", ["Powerbuilding", "Powerlifting", "Hipertrofia", "Weightlifting"])
                    fecha_inicio = st.date_input("Fecha de Inicio")

                    # --- NUEVO: Selector de semanas y días ---
                    col1, col2 = st.columns(2)
                    with col1:
                        semanas = st.number_input("Semanas de duración", min_value=1, max_value=12, value=4)

                    with col2:
                        # Diccionario para mapear texto a los números que usa Python (.weekday())
                        mapa_dias = {
                            "Lunes": 0, "Martes": 1, "Miércoles": 2,
                            "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6
                        }
                        dias_elegidos = st.multiselect(
                            "Días de entrenamiento",
                            options=list(mapa_dias.keys()),
                            default=["Lunes", "Miércoles", "Viernes"] # Por defecto
                        )

                    if st.form_submit_button("Construir Esqueleto"):
                        if not nombre_meso:
                            st.error("Debes darle un nombre al mesociclo.")
                        elif not dias_elegidos:
                            st.error("Debes seleccionar al menos un día de entrenamiento.")
                        else:
                            # Convertimos los textos ("Lunes") a sus números (0)
                            numeros_dias = [mapa_dias[dia] for dia in dias_elegidos]

                            if grupo_seleccionado:
                                datos_manual = {
                                    "group_id": grupo_seleccionado,
                                    "name": nombre_meso,
                                    "discipline": disciplina,
                                    "start_date": str(fecha_inicio),
                                    "weeks_count": semanas,
                                    "training_days": numeros_dias
                                }
                                res_manual = requests.post(f"{API_URL}/mesocycles/manual/group", json=datos_manual, headers=get_headers())
                                if res_manual.status_code == 200:
                                    st.success(res_manual.json().get("message", "¡Cascarones creados para el grupo!"))
                                    st.info("Ve a '🔍 Ver Rutinas' para añadir los ejercicios a estos días.")
                                else:
                                    st.error(f"Error al crear el mesociclo: {res_manual.text}")
                            else:
                                datos_manual = {
                                    "user_id": atleta_seleccionado,
                                    "name": nombre_meso,
                                    "discipline": disciplina,
                                    "start_date": str(fecha_inicio),
                                    "weeks_count": semanas,
                                    "training_days": numeros_dias
                                }
                                res_manual = requests.post(f"{API_URL}/mesocycles/manual", json=datos_manual, headers=get_headers())
                                if res_manual.status_code == 200:
                                    st.success(f"¡Cascarón creado con éxito! Se programaron {res_manual.json().get('total_sessions', 0)} sesiones.")
                                    st.info("Ve a '🔍 Ver Rutinas' para añadir los ejercicios a estos días.")
                                else:
                                    st.error("Error al crear el mesociclo.")
        
    elif usuario_actual["role"] == "athlete":
        # ==========================================
        # INTERFAZ DEL ATLETA
        # ==========================================
        st.title(f"Tus Entrenamientos, {usuario_actual['full_name']} 🏋️")
        my_id = usuario_actual["id"]

        opcion = st.sidebar.radio("Navegación", ["📅 Mi Entrenamiento", "📈 Mis Récords (PRs)"])

        # ==========================================
        # SECCIÓN: MI ENTRENAMIENTO
        # ==========================================
        if opcion == "📅 Mi Entrenamiento":
            st.subheader("📅 Mi Entrenamiento")

            res_mesos = requests.get(f"{API_URL}/users/{my_id}/mesocycles/", headers=get_headers())
            if res_mesos.status_code == 200 and res_mesos.json():
                mesociclos = sorted(
                    res_mesos.json(),
                    key=lambda m: (not m.get("is_active", True), m["start_date"]),
                )
                opciones_meso = {
                    f"{'🟢' if m.get('is_active') else '⚪'} {m.get('name', 'Rutina')} - {m['discipline']} ({m['start_date']})": m["id"]
                    for m in mesociclos
                }
                meso_sel = st.selectbox("Selecciona tu mesociclo:", list(opciones_meso.keys()))
                meso_id = opciones_meso[meso_sel]

                res_detalle = requests.get(f"{API_URL}/mesocycles/{meso_id}", headers=get_headers())
                if res_detalle.status_code == 200:
                    datos = res_detalle.json()
                    sesiones = datos.get("sessions", [])

                    # Separamos las sesiones "normales" de sus versiones adaptadas al tiempo
                    # (mismo día, pero un plan más corto que el atleta pidió sobre la marcha).
                    originales = [s for s in sesiones if not s.get("parent_session_id")]
                    adaptadas_por_padre = {
                        s["parent_session_id"]: s for s in sesiones if s.get("parent_session_id")
                    }

                    hoy = datetime.date.today().isoformat()
                    sesion_hoy = next((s for s in originales if s["scheduled_date"] == hoy), None)

                    if sesion_hoy:
                        st.success(f"🔥 ¡Hoy tienes entrenamiento programado! ({hoy})")
                        render_athlete_session_with_adapt(sesion_hoy, adaptadas_por_padre.get(sesion_hoy["id"]))
                        st.markdown("---")

                    st.markdown("##### 📖 Todas las sesiones de este mesociclo")
                    if not originales:
                        st.info("Este mesociclo todavía no tiene sesiones.")
                    for sesion in originales:
                        if sesion_hoy and sesion["id"] == sesion_hoy["id"]:
                            continue  # ya se mostró destacada arriba
                        estado_icono = "✅" if sesion["status"] == "completed" else "⏳"
                        with st.expander(f"{estado_icono} {sesion['scheduled_date']}"):
                            render_athlete_session_with_adapt(sesion, adaptadas_por_padre.get(sesion["id"]))
                else:
                    st.error("Error al cargar el mesociclo.")
            else:
                st.info("Todavía no tienes ningún mesociclo asignado. Pide a tu coach que te programe uno.")

        # ==========================================
        # SECCIÓN: MIS RÉCORDS (PRs)
        # ==========================================
        elif opcion == "📈 Mis Récords (PRs)":
            st.subheader("📈 Mis Récords (PRs)")

            res_prs = requests.get(f"{API_URL}/users/{my_id}/records/", headers=get_headers())
            if res_prs.status_code == 200:
                marcas = res_prs.json()
                if marcas:
                    cols = st.columns(4)
                    for i, marca in enumerate(marcas):
                        with cols[i % 4]:
                            fecha = marca['last_updated'].split("T")[0]
                            st.metric(
                                label=marca['exercise_name'],
                                value=f"{marca['max_weight_kg']} kg",
                                delta=f"Último test: {fecha}",
                                delta_color="off"
                            )
                else:
                    st.info("Todavía no tienes marcas registradas. ¡Registra la primera abajo!")
            else:
                st.error("Error al cargar tus marcas.")

            st.markdown("---")
            st.write("**Registrar nueva marca**")
            with st.form("form_nuevo_pr_atleta"):
                col1, col2 = st.columns(2)
                with col1:
                    ejercicio = st.text_input("Ejercicio (Ej: Back Squat, Snatch)")
                with col2:
                    peso = st.number_input("1RM en kg", min_value=0.0, step=2.5)

                if st.form_submit_button("Guardar Marca"):
                    if ejercicio:
                        res_pr = requests.post(
                            f"{API_URL}/users/{my_id}/records/",
                            json={"exercise_name": ejercicio, "max_weight_kg": peso},
                            headers=get_headers()
                        )
                        if res_pr.status_code == 200:
                            st.success(f"¡Marca de {ejercicio} actualizada a {peso}kg!")
                            st.rerun()
                        else:
                            st.error("Error al guardar la marca.")
                    else:
                        st.warning("Escribe el nombre del ejercicio.")

            # ==========================================
            # MÓDULO: CALCULADORA DE FIT LEVEL
            # ==========================================
            st.markdown("---")
            st.subheader("🎯 Calcula tu Fit Level")
            st.caption(
                "Estándares aproximados y genéricos (no diferenciados por sexo/edad) — úsalos "
                "como referencia, no como medición oficial. Llena solo las marcas que ya tengas; "
                "entre más completes, más preciso será tu resultado."
            )

            res_fit = requests.get(f"{API_URL}/users/{my_id}/fitness-level", headers=get_headers())
            datos_fit = res_fit.json() if res_fit.status_code == 200 else {}
            valores_actuales = datos_fit.get("values", {})
            peso_actual = datos_fit.get("body_weight")

            iconos_cat = {"halterofilia": "🏋️", "gimnasia": "🤸", "metcon": "🔥"}
            nombres_cat = {"halterofilia": "Halterofilia", "gimnasia": "Gimnasia", "metcon": "Metcon"}

            if datos_fit.get("overall_level"):
                st.markdown(f"### ⭐ Nivel General: {datos_fit['overall_level']} ({datos_fit['overall_score']}/4)")
                cols_niveles = st.columns(3)
                for i, cat in enumerate(["halterofilia", "gimnasia", "metcon"]):
                    with cols_niveles[i]:
                        nivel = datos_fit.get("category_levels", {}).get(cat)
                        if nivel:
                            st.metric(f"{iconos_cat[cat]} {nombres_cat[cat]}", nivel, f"{datos_fit['category_scores'][cat]}/4")
                        else:
                            st.metric(f"{iconos_cat[cat]} {nombres_cat[cat]}", "Sin datos")
            else:
                st.info("Todavía no has registrado marcas para calcular tu Fit Level. Llena el formulario de abajo.")

            with st.expander("✏️ Llenar / actualizar mis marcas"):
                with st.form("form_fit_level"):
                    peso_corporal = st.number_input(
                        "Peso corporal (kg) — necesario para halterofilia",
                        min_value=0.0, step=0.5, value=float(peso_actual) if peso_actual else 0.0
                    )

                    st.markdown("##### 🏋️ Halterofilia (1RM en kg)")
                    c1, c2 = st.columns(2)
                    with c1:
                        snatch = st.number_input("Snatch", min_value=0.0, step=1.0, value=float(valores_actuales.get("snatch_kg") or 0))
                        back_squat = st.number_input("Back Squat", min_value=0.0, step=1.0, value=float(valores_actuales.get("back_squat_kg") or 0))
                    with c2:
                        clean_jerk = st.number_input("Clean & Jerk", min_value=0.0, step=1.0, value=float(valores_actuales.get("clean_jerk_kg") or 0))
                        deadlift = st.number_input("Deadlift", min_value=0.0, step=1.0, value=float(valores_actuales.get("deadlift_kg") or 0))

                    st.markdown("##### 🤸 Gimnasia (repeticiones máximas)")
                    c3, c4 = st.columns(2)
                    with c3:
                        pull_ups = st.number_input("Dominadas estrictas", min_value=0, step=1, value=int(valores_actuales.get("pull_ups_max") or 0))
                        muscle_ups = st.number_input("Muscle-ups", min_value=0, step=1, value=int(valores_actuales.get("muscle_ups_max") or 0))
                    with c4:
                        push_ups = st.number_input("Push-ups", min_value=0, step=1, value=int(valores_actuales.get("push_ups_max") or 0))
                        hspu = st.number_input("Handstand push-ups", min_value=0, step=1, value=int(valores_actuales.get("hspu_max") or 0))

                    st.markdown("##### 🔥 Metcon")
                    st.caption(
                        "Fran: 21-15-9 Thrusters + Pull-ups · Grace: 30 Clean & Jerks · "
                        "Cindy: AMRAP 20min (5 pull-ups, 10 push-ups, 15 air squats) · Remo 2000m"
                    )

                    def _tiempo_input(label, key_prefix, valor_actual_seg):
                        minutos_default = int((valor_actual_seg or 0) // 60)
                        segundos_default = int((valor_actual_seg or 0) % 60)
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            m = st.number_input(f"{label} - min", min_value=0, step=1, value=minutos_default, key=f"{key_prefix}_min")
                        with cc2:
                            s = st.number_input(f"{label} - seg", min_value=0, max_value=59, step=1, value=segundos_default, key=f"{key_prefix}_seg")
                        return m * 60 + s

                    fran_seg = _tiempo_input("Fran", "fran", valores_actuales.get("fran_seconds"))
                    grace_seg = _tiempo_input("Grace", "grace", valores_actuales.get("grace_seconds"))
                    row_seg = _tiempo_input("Remo 2000m", "row2k", valores_actuales.get("row_2k_seconds"))
                    cindy_reps = st.number_input("Cindy - reps totales completadas", min_value=0, step=1, value=int(valores_actuales.get("cindy_total_reps") or 0))

                    if st.form_submit_button("💾 Guardar y calcular Fit Level"):
                        payload = {}
                        if peso_corporal > 0:
                            payload["body_weight"] = peso_corporal
                        if snatch > 0:
                            payload["snatch_kg"] = snatch
                        if clean_jerk > 0:
                            payload["clean_jerk_kg"] = clean_jerk
                        if back_squat > 0:
                            payload["back_squat_kg"] = back_squat
                        if deadlift > 0:
                            payload["deadlift_kg"] = deadlift
                        if pull_ups > 0:
                            payload["pull_ups_max"] = pull_ups
                        if push_ups > 0:
                            payload["push_ups_max"] = push_ups
                        if muscle_ups > 0:
                            payload["muscle_ups_max"] = muscle_ups
                        if hspu > 0:
                            payload["hspu_max"] = hspu
                        if fran_seg > 0:
                            payload["fran_seconds"] = fran_seg
                        if grace_seg > 0:
                            payload["grace_seconds"] = grace_seg
                        if row_seg > 0:
                            payload["row_2k_seconds"] = row_seg
                        if cindy_reps > 0:
                            payload["cindy_total_reps"] = cindy_reps

                        res_save = requests.put(
                            f"{API_URL}/users/{my_id}/fitness-benchmarks", json=payload, headers=get_headers()
                        )
                        if res_save.status_code == 200:
                            st.success("¡Marcas guardadas! Tu Fit Level se actualizó.")
                            st.rerun()
                        else:
                            st.error(f"Error al guardar: {res_save.text}")

    elif usuario_actual["role"] == "admin":
        # ==========================================
        # INTERFAZ DEL ADMINISTRADOR
        # ==========================================
        st.title("Panel de Administración 🛡️")
        st.caption("Visibilidad y control total sobre toda la app: todos los coaches, atletas, grupos y mesociclos.")

        opcion = st.sidebar.radio("Navegación", ["📊 Resumen General", "👥 Todos los Usuarios", "👨‍👩‍👧‍👦 Todos los Grupos"])

        # ==========================================
        # SECCIÓN: RESUMEN GENERAL
        # ==========================================
        if opcion == "📊 Resumen General":
            st.subheader("📊 Resumen General")
            res_overview = requests.get(f"{API_URL}/admin/overview", headers=get_headers())
            if res_overview.status_code == 200:
                d = res_overview.json()
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Usuarios totales", d["total_users"])
                col2.metric("Coaches", d["total_coaches"])
                col3.metric("Atletas", d["total_athletes"])
                col4.metric("Admins", d["total_admins"])

                st.markdown("---")
                col5, col6, col7 = st.columns(3)
                col5.metric("Grupos", d["total_groups"])
                col6.metric("Mesociclos", d["total_mesocycles"])
                col7.metric("Sesiones totales", d["total_sessions"])

                col8, col9 = st.columns(2)
                col8.metric("✅ Sesiones completadas", d["sessions_completed"])
                col9.metric("⏳ Sesiones pendientes", d["sessions_pending"])
            else:
                st.error("Error al cargar el resumen.")

        # ==========================================
        # SECCIÓN: TODOS LOS USUARIOS
        # ==========================================
        elif opcion == "👥 Todos los Usuarios":
            st.subheader("👥 Todos los Usuarios")
            res_users = requests.get(f"{API_URL}/users/", headers=get_headers())
            if res_users.status_code == 200 and res_users.json():
                roles_disponibles = ["athlete", "coach", "admin"]
                for u in res_users.json():
                    col1, col2, col3, col4 = st.columns([2.7, 1.2, 1, 1.3])
                    with col1:
                        st.write(f"**{u['full_name']}** — {u['email']}")
                    with col2:
                        nuevo_rol = st.selectbox(
                            "Rol", roles_disponibles, index=roles_disponibles.index(u['role']),
                            key=f"rol_{u['id']}", label_visibility="collapsed"
                        )
                    with col3:
                        if nuevo_rol != u['role'] and st.button("Guardar", key=f"guardar_rol_{u['id']}"):
                            res = requests.put(
                                f"{API_URL}/admin/users/{u['id']}/role",
                                json={"role": nuevo_rol}, headers=get_headers()
                            )
                            if res.status_code == 200:
                                st.success(f"Rol de {u['full_name']} actualizado a '{nuevo_rol}'")
                                st.rerun()
                            else:
                                try:
                                    st.error(res.json().get("detail", "Error al actualizar el rol"))
                                except Exception:
                                    st.error("Error al actualizar el rol.")
                    with col4:
                        if st.button("🚫 Revocar sesiones", key=f"revocar_{u['id']}"):
                            res_rev = requests.post(
                                f"{API_URL}/admin/users/{u['id']}/revoke-sessions", headers=get_headers()
                            )
                            if res_rev.status_code == 200:
                                st.success(res_rev.json().get("message"))
                            else:
                                st.error("Error al revocar las sesiones.")
                    st.markdown("---")
            else:
                st.info("No hay usuarios registrados todavía.")

        # ==========================================
        # SECCIÓN: TODOS LOS GRUPOS
        # ==========================================
        elif opcion == "👨‍👩‍👧‍👦 Todos los Grupos":
            st.subheader("👨‍👩‍👧‍👦 Todos los Grupos")
            res_grupos = requests.get(f"{API_URL}/groups/", headers=get_headers())
            if res_grupos.status_code == 200 and res_grupos.json():
                for grupo in res_grupos.json():
                    titulo = f"👥 {grupo['name']} — coach: {grupo.get('coach_name') or '?'} ({grupo['member_count']} atleta(s))"
                    with st.expander(titulo):
                        render_group_programs(grupo["id"])
            else:
                st.info("No hay grupos en el sistema todavía.")