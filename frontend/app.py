import streamlit as st
import requests
import extra_streamlit_components as stx
import datetime 

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

# Función auxiliar para enviar el token como un "Pase VIP"
def get_headers():
    if jwt_token:
        return {"Authorization": f"Bearer {jwt_token}"}
    return {}

# 2. HIDRATACIÓN: Si hay token en la cookie, pero Streamlit olvidó quién eres, le preguntamos al backend
if jwt_token and st.session_state.user_session is None:
    # Usamos la nueva ruta /auth/me enviando el token en las cabeceras
    res_me = requests.get(f"{API_URL}/auth/me", headers=get_headers())
    if res_me.status_code == 200:
        st.session_state.user_session = res_me.json()
    else:
        # Si el token expiró o es falso, lo destruimos
        cookie_manager.delete("neurolift_jwt", key="delete_invalid")
        st.session_state.user_session = None

# ==========================================
# PANTALLA DE LOGIN / REGISTRO
# ==========================================
if st.session_state.user_session is None:
    st.title("Bienvenido a NeuroLift 🧠")
    st.subheader("La plataforma inteligente de entrenamiento")
    
    tab_login, tab_register = st.tabs(["🔑 Iniciar Sesión", "📝 Crear Cuenta"])
    
    with tab_login:
        with st.form("form_login"):
            log_email = st.text_input("Correo electrónico")
            log_pass = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                res = requests.post(f"{API_URL}/auth/login", json={"email": log_email, "password": log_pass})
                
                if res.status_code == 200:
                    datos_token = res.json()
                    token = datos_token["access_token"]
                    
                    # 1. Guardamos el TOKEN en la cookie para el futuro
                    cookie_manager.set("neurolift_jwt", token, key="set_jwt_login")
                    
                    # 2. Vamos de inmediato al backend a traer tus datos reales ("Hidratación" manual)
                    res_me = requests.get(f"{API_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
                    
                    if res_me.status_code == 200:
                        # 3. Te metemos al sistema manualmente
                        st.session_state.user_session = res_me.json()
                        st.success("¡Autenticación exitosa! Entrando...")
                        st.rerun()
                    else:
                        st.error("Error al obtener el perfil de usuario.")
                else:
                    st.error("Credenciales incorrectas")
                    
    with tab_register:
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
                    st.success("¡Cuenta creada exitosamente! Ve a Iniciar Sesión.")
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
        st.write(f"🏷️ Rol: {'Coach' if usuario_actual.get('role') == 'coach' else 'Atleta'}")
        
        if st.button("Cerrar Sesión"):
            st.session_state.user_session = None
            cookie_manager.delete("neurolift_jwt", key="delete_jwt_logout")
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
            ["👥 Nuevo Atleta", "⚙️ Crear Mesociclo con IA", "✍️ Crear Mesociclo Manual", "🔍 Ver Rutinas", "💪 Toma de Marcas (PRs)"]
        )
        
       # ==========================================
        # SECCIÓN: NUEVO ATLETA
        # ==========================================
        if opcion == "👥 Nuevo Atleta":
            st.subheader("👥 Registrar Nuevo Atleta")
            with st.form("form_nuevo_atleta"):
                nombre = st.text_input("Nombre completo")
                correo = st.text_input("Correo electrónico")
                peso = st.number_input("Peso corporal (kg)", min_value=0.0, step=0.5, value=70.0) # <-- ¡Nuevo campo!
                
                submit_btn = st.form_submit_button("Registrar Atleta")
                
                if submit_btn and nombre and correo:
                    # Ahora sí enviamos el paquete completo con el peso
                    datos_atleta = {
                        "full_name": nombre, 
                        "email": correo, 
                        "body_weight": peso
                    }
                    res = requests.post(f"{API_URL}/users/", json=datos_atleta)
                    
                    if res.status_code == 200:
                        st.success(f"¡Atleta {nombre} registrado con éxito!")
                    elif res.status_code == 400:
                        # Manejamos el clásico error de correo duplicado
                        st.error("Error 400: Es posible que este correo ya esté registrado.")
                    else:
                        st.error(f"Error del servidor: {res.text}")

        # ==========================================
        # SECCIÓN: CREAR MESOCICLO
        # ==========================================
        elif opcion == "⚙️ Crear Mesociclo con IA":
            st.subheader("🤖 Generar Mesociclo con IA")
            st.markdown("Diseña la estructura y deja que Gemini calcule los volúmenes, ejercicios y porcentajes.")
            
            # Traer lista de atletas
            res_atletas = requests.get(f"{API_URL}/users/athletes", headers=get_headers())
            
            if res_atletas.status_code == 200 and res_atletas.json():
                atletas = res_atletas.json()
                opciones_atletas = {a["id"]: a["full_name"] for a in atletas}
                
                with st.form("form_ia_meso"):
                    atleta_seleccionado = st.selectbox(
                        "Seleccionar Atleta", 
                        options=list(opciones_atletas.keys()), 
                        format_func=lambda x: opciones_atletas[x]
                    )
                    
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
                        
                    if st.form_submit_button("✨ Generar con Inteligencia Artificial"):
                            if not nombre_meso:
                                st.error("Debes darle un nombre al mesociclo.")
                            elif not dias_elegidos:
                                st.error("Selecciona al menos un día de entrenamiento.")
                            else:
                                numeros_dias = [mapa_dias[dia] for dia in dias_elegidos]
                                
                                # Datos limpios y estructurados
                                datos_ia = {
                                    "user_id": atleta_seleccionado,
                                    "name": nombre_meso,
                                    "discipline": disciplina,
                                    "start_date": str(fecha_inicio),
                                    "weeks_count": semanas,
                                    "training_days": numeros_dias,
                                    "context": objetivo if objetivo else "Progreso lineal y mejora técnica general."
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
            
            # 1. Filtramos primero por el Atleta
            res_usuarios = requests.get(f"{API_URL}/users/")
            if res_usuarios.status_code == 200 and len(res_usuarios.json()) > 0:
                usuarios = res_usuarios.json()
                opciones_usuarios = {u['full_name']: u['id'] for u in usuarios}
                
                atleta_seleccionado = st.selectbox("1. Selecciona al Atleta:", list(opciones_usuarios.keys()))
                user_id = opciones_usuarios[atleta_seleccionado]
                
                # 2. Buscamos los mesociclos SOLO de ese atleta
                res_meso = requests.get(f"{API_URL}/users/{user_id}/mesocycles/")
                if res_meso.status_code == 200 and len(res_meso.json()) > 0:
                    mesociclos = res_meso.json()
                    opciones_meso = {f"🏋️ {m.get('name', 'Rutina')} - {m['discipline']} ({m['start_date']})": m['id'] for m in mesociclos}
                    
                    meso_seleccionado = st.selectbox("2. Selecciona el Mesociclo:", list(opciones_meso.keys()))
                    meso_id = opciones_meso[meso_seleccionado]
                    
                    st.markdown("---")
                    
                    # 3. Traemos el detalle completo para editar
                    res_detalle = requests.get(f"{API_URL}/mesocycles/{meso_id}")
                    if res_detalle.status_code == 200:
                        datos = res_detalle.json()
                        
                        
                        # Iteramos sobre las sesiones
                        for sesion in datos.get("sessions", []):
                            
                                dias_espanol = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                                
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
                                
                                # Nuestro nuevo y hermoso título
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
                                                    requests.put(f"{API_URL}/sets/{plan['original_ids'][i]}", json=plan["data"])
                                                
                                                if plan["num_nuevo"] < plan["num_original"]:
                                                    for i in range(plan["num_nuevo"], plan["num_original"]):
                                                        requests.delete(f"{API_URL}/sets/{plan['original_ids'][i]}")
                                                        
                                                elif plan["num_nuevo"] > plan["num_original"]:
                                                    series_a_crear = plan["num_nuevo"] - plan["num_original"]
                                                    for _ in range(series_a_crear):
                                                        requests.post(f"{API_URL}/sessions/{plan['session_id']}/sets/", json=plan["data"])
                                                        
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
                                                    requests.post(f"{API_URL}/sessions/{sesion['id']}/sets/", json=datos_nuevo)
                                                st.success(f"¡Ejercicio añadido con {nuevo_ej_series} series!")
                                                st.rerun()
                                            else:
                                                st.warning("Debes escribir el nombre del ejercicio.")
                    else:
                        st.error("Error al cargar los detalles del mesociclo.")
                else:
                    st.info("Este atleta aún no tiene mesociclos generados.")
            else:
                st.warning("Primero debes registrar un atleta en la pestaña 'Nuevo Atleta'.")

        if opcion == "Ver Mesociclo":
            st.subheader("🔍 Consultar Rutina Existente")
            
            # 1. Le pedimos al backend la lista de todos los mesociclos
            try:
                respuesta_lista = requests.get(f"{API_URL}/mesocycles/")
                
                if respuesta_lista.status_code == 200:
                    lista_mesociclos = respuesta_lista.json()
                    
                    if len(lista_mesociclos) > 0:
                        # 2. Creamos un diccionario: { "Texto Amigable": "UUID" }
                        opciones_nombres = {
                            f"🏋️ {m['discipline']} (Inicia: {m['start_date']})": m['id'] 
                            for m in lista_mesociclos
                        }
                        
                        # 3. Mostramos el Selectbox amigable al usuario
                        seleccion = st.selectbox("Selecciona tu rutina:", list(opciones_nombres.keys()))
                        
                        # 4. Extraemos el UUID real escondido detrás de esa selección
                        meso_id = opciones_nombres[seleccion]
                        
                        if st.button("Cargar Rutina"):
                            with st.spinner("Descargando sesiones..."):
                                # Llamamos al endpoint gigante que ya teníamos
                                res_detalle = requests.get(f"{API_URL}/mesocycles/{meso_id}")
                                
                                if res_detalle.status_code == 200:
                                    datos = res_detalle.json()
                                    st.success(f"¡Rutina cargada con éxito!")
                                    
                                    for sesion in datos.get("sessions", []):
                                        with st.expander(f"📅 Sesión: {sesion['scheduled_date']} | {sesion.get('athlete_notes', '')}"):
                                            for set_data in sesion.get("sets", []):
                                                ejercicio = set_data["exercise"]["name"]
                                                reps = set_data["prescribed_reps"]
                                                rpe = set_data["rpe"]
                                                st.write(f"🔹 **{ejercicio}** - {reps} reps @ RPE {rpe}")
                                else:
                                    st.error("Error al cargar los detalles.")
                    else:
                        st.info("Aún no hay mesociclos en la base de datos.")
            except Exception as e:
                st.error("Error de conexión con el backend. ¿Está corriendo FastAPI?")

        elif opcion == "Crear Rutina":
            st.subheader("⚙️ Generar Nuevo Mesociclo")
            st.info("Aquí conectaremos los endpoints de creación pronto.")

        # ==========================================
        # SECCIÓN: TOMA DE MARCAS (RMs)
        # ==========================================
        elif opcion == "💪 Toma de Marcas (PRs)":
            st.subheader("💪 Toma de Marcas y Perfil de Fuerza")
            
            res_usuarios = requests.get(f"{API_URL}/users/")
            
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
                res_prs = requests.get(f"{API_URL}/users/{user_id}/records/")
                
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
                        res_pr = requests.post(f"{API_URL}/users/{user_id}/records/", json=datos_pr)
                        
                        if res_pr.status_code == 200:
                            st.success(f"¡Marca de {ejercicio} actualizada a {peso}kg!")
                            # Un pequeño truco para recargar la página y ver el nuevo PR al instante
                            st.rerun() 
                        else:
                            st.error("Error al guardar la marca.")
        elif opcion == "✍️ Crear Mesociclo Manual":
            st.subheader("✍️ Creación Manual de Mesociclo")
            st.markdown("Genera el esqueleto de tu mesociclo y llénalo de ejercicios en la pestaña **🔍 Ver Rutinas**.")
            
            # Traer lista de atletas desde la API
            res_atletas = requests.get(f"{API_URL}/users/athletes")
            
            if res_atletas.status_code == 200:
                atletas = res_atletas.json()
                
                if not atletas:
                    st.warning("No tienes atletas registrados. Pide a tus clientes que creen su cuenta como 'Atleta'.")
                else:
                    # Diccionario para mapear ID -> Nombre Completo
                    opciones_atletas = {a["id"]: a["full_name"] for a in atletas}
                    
                    with st.form("form_manual_meso"):
                        atleta_seleccionado = st.selectbox(
                            "Seleccionar Atleta", 
                            options=list(opciones_atletas.keys()), 
                            format_func=lambda x: opciones_atletas[x]
                        )
                        
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
                                
                                datos_manual = {
                                    "user_id": atleta_seleccionado,
                                    "name": nombre_meso,
                                    "discipline": disciplina,
                                    "start_date": str(fecha_inicio),
                                    "weeks_count": semanas,
                                    "training_days": numeros_dias
                                }
                                
                                res_manual = requests.post(f"{API_URL}/mesocycles/manual", json=datos_manual)
                                
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
        
        opcion = st.sidebar.radio("Navegación", ["📅 Mi Rutina de Hoy", "📈 Mis Récords (PRs)"])
        
        if opcion == "📅 Mi Rutina de Hoy":
            st.info("Aquí cargaremos tu entrenamiento del día. Próximamente.")
            # Aquí filtraremos los mesociclos usando usuario_actual["id"]
            
        elif opcion == "📈 Mis Récords (PRs)":
            st.info("Aquí podrás ver y actualizar tu Back Squat, Bench Press, etc.")