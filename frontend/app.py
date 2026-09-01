import streamlit as st
import requests

# La dirección de tu backend (FastAPI)
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="NeuroLift AI", page_icon="🏋️‍♂️", layout="wide")

st.title("🏋️‍♂️ NeuroLift - Panel de Coach AI")
st.markdown("Bienvenido al generador de mesociclos inteligente.")

# --- Menú Lateral ---
st.sidebar.header("Menú del Entrenador")
opciones_menu = ["🔍 Ver Rutinas", "👥 Nuevo Atleta", "💪 Toma de Marcas (PRs)", "⚙️ Crear Mesociclo con IA"]
opcion = st.sidebar.radio("Navegación:", opciones_menu)

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
    st.subheader("⚙️ Programador Inteligente")
    
    # 1. Traer lista de atletas
    res_usuarios = requests.get(f"{API_URL}/users/")
    if res_usuarios.status_code == 200 and len(res_usuarios.json()) > 0:
        usuarios = res_usuarios.json()
        opciones_usuarios = {u['full_name']: u['id'] for u in usuarios}
        
        # Formulario de 2 pasos integrados
        atleta_seleccionado = st.selectbox("Selecciona al Atleta:", list(opciones_usuarios.keys()))
        disciplina = st.selectbox("Disciplina:", ["Levantamiento Olímpico", "Powerlifting", "Hipertrofia", "Readaptación"])
        fecha_inicio = st.date_input("Fecha de Inicio")
        
        st.markdown("---")
        st.markdown("**Parámetros de la Inteligencia Artificial**")
        semanas = st.number_input("Cantidad de semanas", min_value=1, max_value=12, value=4)
        dias_por_semana = st.number_input("Días de entrenamiento por semana", min_value=1, max_value=7, value=4)
        contexto = st.text_area("Contexto del Atleta (Lesiones, objetivos, puntos débiles...)", 
                                placeholder="Ej: Atleta principiante, necesita mejorar técnica en el Snatch...")
        
        if st.button("🚀 Generar Mesociclo Completo"):
            with st.spinner("Construyendo rutina con base científica... Esto puede tomar unos segundos."):
                # Paso A: Crear el Cascarón
                datos_cascaron = {
                    "user_id": opciones_usuarios[atleta_seleccionado],
                    "discipline": disciplina,
                    "start_date": str(fecha_inicio)
                }
                res_cascaron = requests.post(f"{API_URL}/mesocycles/", json=datos_cascaron)
                
                if res_cascaron.status_code == 200:
                    meso_id = res_cascaron.json()["id"]
                    
                    # Paso B: Inyectar la IA
                    datos_ia = {
                        "mesocycle_id": meso_id,
                        "context": contexto,
                        "weeks_count": semanas,
                        "sessions_per_week": dias_por_semana
                    }
                    res_ia = requests.post(f"{API_URL}/ai/generate-full-mesocycle/", json=datos_ia)
                    
                    if res_ia.status_code == 200:
                        st.success(f"¡Éxito! {res_ia.json()['message']}")
                        st.info(f"Foco principal: {res_ia.json().get('focus', '')}")
                        st.balloons() # ¡Un toque visual de celebración!
                    else:
                        st.error(f"Error en IA: {res_ia.text}")
                else:
                    st.error("Error al crear el cascarón del mesociclo.")
    else:
        st.warning("Primero debes registrar un atleta en la pestaña 'Nuevo Atleta'.")

# ==========================================
# SECCIÓN: VER RUTINAS (Lo que ya tenías)
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
            opciones_meso = {f"🏋️ {m['discipline']} (Inicia: {m['start_date']})": m['id'] for m in mesociclos}
            
            meso_seleccionado = st.selectbox("2. Selecciona el Mesociclo:", list(opciones_meso.keys()))
            meso_id = opciones_meso[meso_seleccionado]
            
            st.markdown("---")
            
            # 3. Traemos el detalle completo para editar
            res_detalle = requests.get(f"{API_URL}/mesocycles/{meso_id}")
            if res_detalle.status_code == 200:
                datos = res_detalle.json()
                st.write(f"### 📋 Panel de Edición - {atleta_seleccionado}")
                
                # Iteramos sobre las sesiones y creamos un formulario por cada una
                for sesion in datos.get("sessions", []):
                    with st.expander(f"📅 Sesión: {sesion['scheduled_date']} | {sesion.get('athlete_notes', '')}"):
                        
                        # Usamos un form para que el Coach haga todos los cambios de una sesión y guarde al final
                        with st.form(f"form_sesion_{sesion['id']}"):
                            cambios_series = {} # Aquí guardaremos lo que el Coach modifique
                            
                            for set_data in sesion.get("sets", []):
                                col1, col2, col3 = st.columns([2, 1, 1])
                                set_id = set_data["id"]
                                
                                with col1:
                                    st.markdown(f"**{set_data['exercise']['name']}**")
                                with col2:
                                    # El Coach puede editar las reps, mostrando las que sugirió la IA por defecto
                                    nuevas_reps = st.number_input("Reps", value=int(set_data["prescribed_reps"]), key=f"reps_{set_id}")
                                with col3:
                                    # El Coach puede editar el RPE
                                    rpe_actual = float(set_data.get("rpe")) if set_data.get("rpe") else 0.0
                                    nuevo_rpe = st.number_input("RPE", value=rpe_actual, key=f"rpe_{set_id}")
                                
                                # Almacenamos el estado de los inputs
                                cambios_series[set_id] = {"prescribed_reps": nuevas_reps, "rpe": nuevo_rpe}
                            
                            # Botón para impactar la base de datos
                            if st.form_submit_button("💾 Guardar Ajustes de esta Sesión"):
                                for s_id, valores in cambios_series.items():
                                    requests.put(f"{API_URL}/sets/{s_id}", json=valores)
                                st.success("¡Ajustes guardados con éxito!")
                                
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