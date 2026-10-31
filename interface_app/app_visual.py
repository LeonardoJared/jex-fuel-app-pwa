import streamlit as st
import requests
import datetime
import os
import pandas as pd
import base64

# ===========================================================================
# RESOLUCIÓN SEGURA DE RUTAS (Tolerante a ejecuciones desde cualquier carpeta)
# ===========================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(CURRENT_DIR, "assets")
CSS_FILE = os.path.join(CURRENT_DIR, "styles.css")
ICON_FILE = os.path.join(ASSETS_DIR, "logo_jex.ico")
LOGO_FILE = os.path.join(ASSETS_DIR, "logo_jex.png")

st.set_page_config(
    page_title="JEX Technologies - Fuel", 
    page_icon=ICON_FILE if os.path.exists(ICON_FILE) else "⛽",
    layout="wide", 
    initial_sidebar_state="expanded"
)

def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(CSS_FILE)

# ===========================================================================
# GESTIÓN DE VARIABLES DE ESTADO (SESSION STATE)
# ===========================================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "supervisor_id" not in st.session_state:
    st.session_state.supervisor_id = None
if "equipment_rows" not in st.session_state:
    st.session_state.equipment_rows = []

BACKEND_URL = os.getenv("JEX_BACKEND_URL", "http://localhost:8000")

# ===========================================================================
# PANTALLA DE CONTROL DE ACCESO (LOGIN)
# ===========================================================================
if not st.session_state.logged_in:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    _, col_login_box, _ = st.columns([1, 1.1, 1])
    
    with col_login_box:
        if os.path.exists(LOGO_FILE):
            with open(LOGO_FILE, "rb") as img_file:
                encoded_logo = base64.b64encode(img_file.read()).decode()
            st.markdown(
                f"<div class='login-logo-wrapper'>"
                f"<img src='data:image/png;base64,{encoded_logo}' class='login-logo-img'>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        st.markdown("<h2 class='main-header-title' style='text-align: center;'>INICIAR SESIÓN</h2>", unsafe_allow_html=True)
        
        username_input = st.text_input("USUARIO:", placeholder="ej: nombre.apellido")
        password_input = st.text_input("CONTRASEÑA:", type="password", placeholder="••••••••")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        submit_login = st.button("INGRESAR AL SISTEMA", type="primary", use_container_width=True)
        
        if submit_login:
            if username_input and password_input:
                try:
                    res = requests.post(f"{BACKEND_URL}/api/login", json={
                        "username": username_input.strip(),
                        "password": password_input.strip()
                    }, timeout=15.0)
                    
                    if res.status_code == 200:
                        data = res.json()
                        st.session_state.logged_in = True
                        st.session_state.user_role = str(data["role"]).upper()
                        st.session_state.user_name = data["name"]
                        st.session_state.supervisor_id = data["supervisor_id"]
                        st.rerun()
                    else:
                        st.error(f"❌ {res.json().get('detail', 'Credenciales incorrectas.')}")
                except Exception as e:
                    st.error(f"📡 Error de comunicación con el backend JEX: {e}")
            else:
                st.warning("⚠️ Complete todos los campos.")
    st.stop()

# ===========================================================================
# FUNCIONES DE CATÁLOGOS CON CACHÉ RESILIENTE
# ===========================================================================
@st.cache_data(ttl=180)
def obtener_catalogo_supervisores():
    try: 
        res = requests.get(f"{BACKEND_URL}/api/supervisors", timeout=10.0)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

@st.cache_data(ttl=180)
def obtener_catalogo_operadores():
    try: 
        res = requests.get(f"{BACKEND_URL}/api/operators", timeout=10.0)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

@st.cache_data(ttl=180)
def obtener_catalogo_cisternas():
    try: 
        res = requests.get(f"{BACKEND_URL}/api/fuel-trucks", timeout=10.0)
        return res.json() if res.status_code == 200 else []
    except Exception: return []

# Diccionarios de mapeo
supervisor_display = {"-": ""}
operator_display = {"-": ""}
truck_display = {"-": ""}

for s in obtener_catalogo_supervisores(): supervisor_display[s["name"]] = s["id"]
for o in obtener_catalogo_operadores(): operator_display[o["name"]] = o["id"]
for t in obtener_catalogo_cisternas(): truck_display[t["name"]] = t["id"]

# ===========================================================================
# BARRA LATERAL (AVATAR Y NAVEGACIÓN)
# ===========================================================================
if st.session_state.supervisor_id:
    foto_usuario = os.path.join(ASSETS_DIR, f"{st.session_state.supervisor_id}.png")
else:
    foto_usuario = os.path.join(ASSETS_DIR, "foto_perfil.png")

if os.path.exists(foto_usuario):
    with open(foto_usuario, "rb") as img_file:
        encoded_img = base64.b64encode(img_file.read()).decode()
    st.sidebar.markdown(
        f"<div class='avatar-container'>"
        f"<img src='data:image/png;base64,{encoded_img}' class='profile-avatar'>"
        f"</div>",
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        f"<div class='avatar-container'>"
        f"<div class='profile-avatar' style='display:flex; align-items:center; justify-content:center; background-color:#1E293B; color:#64748B; font-weight:700; font-size:24px;'>JEX</div>"
        f"</div>",
        unsafe_allow_html=True
    )

st.sidebar.markdown(f"### 👤 {st.session_state.user_name}")
st.sidebar.markdown(f"**Rol:** `{st.session_state.user_role}`")
if st.session_state.supervisor_id:
    st.sidebar.markdown(f"**Código:** `{st.session_state.supervisor_id}`")

st.sidebar.markdown("---")

if st.session_state.user_role in ["ADMINISTRADOR", "ADMIN"]:
    modulos_disponibles = ["📊 Dashboard Corporativo", "👥 Gestión de Maestros", "📋 Historial y Reportes"]
else:
    modulos_disponibles = ["📋 Registrar Despacho"]

modulo_seleccionado = st.sidebar.radio("MÓDULOS DEL SISTEMA:", modulos_disponibles, label_visibility="collapsed")

st.sidebar.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
if st.sidebar.button("🔒 CERRAR SESIÓN", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.session_state.supervisor_id = None
    st.session_state.equipment_rows = []
    st.rerun()

# ===========================================================================
# MODULO: REGISTRAR DESPACHO DE CAMPO
# ===========================================================================
if st.session_state.user_role == "SUPERVISOR" or modulo_seleccionado == "📋 Registrar Despacho":
    st.markdown("<h2 class='main-header-title'>CONTROL DE COMBUSTIBLE</h2>", unsafe_allow_html=True)
    
    st.markdown("<p class='section-title'>Datos Generales de la Operación</p>", unsafe_allow_html=True)
    log_date = st.date_input("Fecha de Operación:", datetime.date.today())
    shift = st.selectbox("Guardia / Turno:", ["-", "DIA", "NOCHE"])
    fuel_type = st.selectbox("Tipo de Combustible:", ["-", "DIESEL B5"])
    selected_operator_name = st.selectbox("Operador de Cisterna:", list(operator_display.keys()))
    operator_id = operator_display.get(selected_operator_name, "")
    selected_truck_plate = st.selectbox("Cisterna (Placa de Unidad):", list(truck_display.keys()))
    truck_id = truck_display.get(selected_truck_plate, "")

    is_form_locked = (shift == "-" or fuel_type == "-" or selected_operator_name == "-" or selected_truck_plate == "-")

    st.markdown("<p class='section-title'>Equipos Despachados</p>", unsafe_allow_html=True)
    equipments_to_send = []
    
    if is_form_locked:
        st.markdown("<div class='info-text-container'>COMPLETE EL FORMULARIO GENERAL PARA HABILITAR LA GRILLA DE DESPACHOS.</div>", unsafe_allow_html=True)
        st.session_state.equipment_rows = []
    else:
        if not st.session_state.equipment_rows:
            st.session_state.equipment_rows.append({"name": "", "code": "", "qty": 0.0})
            
        PROPORCIONES_COLUMNAS = [0.35, 0.35, 0.20, 0.10]
        th1, th2, th3, th4 = st.columns(PROPORCIONES_COLUMNAS)
        th1.markdown("<span style='color:#64748B; font-size:12px; font-weight:700;'>🎯 EQUIPO / MÁQUINA</span>", unsafe_allow_html=True)
        th2.markdown("<span style='color:#64748B; font-size:12px; font-weight:700;'>🔢 CÓDIGO INTERNO</span>", unsafe_allow_html=True)
        th3.markdown("<span style='color:#64748B; font-size:12px; font-weight:700;'>⛽ GALONES (GLN)</span>", unsafe_allow_html=True)
        th4.markdown("<span style='color:#64748B; font-size:12px; font-weight:700; float:right;'>ACCIÓN</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 4px 0 8px 0; border-color: #1E293B;'>", unsafe_allow_html=True)

        rows_to_render = list(st.session_state.equipment_rows)
        for index, row in enumerate(rows_to_render):
            tr1, tr2, tr3, tr4 = st.columns(PROPORCIONES_COLUMNAS)
            
            with tr1:
                eq_name = st.text_input("Name", value=row["name"], key=f"tbl_name_{index}_v6", label_visibility="collapsed", placeholder="Ej: Excavadora CAT 336")
            with tr2:
                eq_code = st.text_input("Code", value=row["code"], key=f"tbl_code_{index}_v6", label_visibility="collapsed", placeholder="Ej: EX-04")
            with tr3:
                eq_qty = st.number_input("Gln", value=row["qty"], min_value=0.0, step=0.1, format="%.1f", key=f"tbl_qty_{index}_v6", label_visibility="collapsed")
            with tr4:
                if st.button("🗑️", key=f"tbl_del_{index}_v6", use_container_width=True, type="secondary"):
                    st.session_state.equipment_rows.pop(index)
                    st.rerun()
            
            st.session_state.equipment_rows[index] = {"name": eq_name, "code": eq_code, "qty": eq_qty}
            
            if eq_name.strip() and eq_code.strip() and eq_qty > 0:
                equipments_to_send.append({
                    "item_number": index + 1,
                    "equipment_name": eq_name.upper().strip(),
                    "equipment_code": eq_code.upper().strip(),
                    "quantity_gln": eq_qty
                })

        c_space, c_add = st.columns([2.8, 1])
        with c_add:
            if st.button("➕ AGREGAR EQUIPO", use_container_width=True, type="secondary", key="btn_add_row"):
                st.session_state.equipment_rows.append({"name": "", "code": "", "qty": 0.0})
                st.rerun()

    st.markdown("<p class='section-title'>Observaciones de Campo</p>", unsafe_allow_html=True)
    remarks = st.text_area("Notas e incidencias:", placeholder="Sin novedades en el despacho...", label_visibility="collapsed")

    if not is_form_locked:
        total_gln = sum(item['quantity_gln'] for item in equipments_to_send)
        k1, k2 = st.columns(2)
        k1.metric("Volumen Total Despachado", f"{total_gln:.1f} GLN")
        k2.metric("Equipos Atendidos", f"{len(equipments_to_send)}")
        
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        if st.button("ENVIAR REPORTE A PLATAFORMA", type="primary", use_container_width=True):
            if not equipments_to_send:
                st.error("⚠️ Debe registrar al menos un equipo con galonaje mayor a cero.")
            elif not st.session_state.supervisor_id:
                st.error("❌ Sesión inválida: Se requiere el código del supervisor activo.")
            else:
                payload = {
                    "log_date": str(log_date), "shift": shift, "fuel_type": fuel_type,
                    "supervisor_id": st.session_state.supervisor_id, 
                    "operator_id": operator_id, "truck_id": truck_id,
                    "remarks": remarks.strip() if remarks.strip() else "Despacho Rutinario",
                    "equipments": equipments_to_send
                }
                try:
                    res = requests.post(f"{BACKEND_URL}/api/fuel-logsheet-complete", json=payload, timeout=12.0)
                    if res.status_code == 200:
                        st.success("🚀 ¡Reporte registrado correctamente en la plataforma central JEX!")
                        st.session_state.equipment_rows = []
                        st.rerun()
                    else:
                        st.error(f"❌ Error en base de datos: {res.json().get('detail', 'No procesado.')}")
                except Exception as e:
                    st.error(f"📡 Error de comunicación con el backend: {e}")

# ===========================================================================
# MODULO: DASHBOARD CORPORATIVO
# ===========================================================================
elif modulo_seleccionado == "📊 Dashboard Corporativo":
    st.markdown("<h2 class='main-header-title'>MONITOREO GENERAL</h2>", unsafe_allow_html=True)
    
    try: 
        res = requests.get(f"{BACKEND_URL}/api/fuel-logs-history", timeout=12.0)
        historial = res.json() if res.status_code == 200 else []
    except Exception: 
        historial = []

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SUPERVISORES", f"{max(len(supervisor_display)-1, 0)}")
    m2.metric("OPERADORES", f"{max(len(operator_display)-1, 0)}")
    m3.metric("CISTERNAS", f"{max(len(truck_display)-1, 0)}")
    m4.metric("DESPACHOS REGISTRADOS", f"{len(historial)}")

    st.markdown("<p class='section-title'>Transacciones Recientes</p>", unsafe_allow_html=True)
    if historial:
        df_dash = pd.DataFrame(historial)
        df_dash.columns = ["ID", "FECHA", "GUARDIA", "COMBUSTIBLE", "SUPERVISOR", "OPERADOR", "PLACA", "DETALLES"]
        st.dataframe(df_dash.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No se registran datos operativos transaccionales en la plataforma.")

# ===========================================================================
# MODULO: GESTIÓN DE MAESTROS (CON CONTROL DE ERRORES)
# ===========================================================================
elif modulo_seleccionado == "👥 Gestión de Maestros":
    st.markdown("<h2 class='main-header-title'>REGISTROS MAESTROS</h2>", unsafe_allow_html=True)
    st.markdown("<p class='section-title'>Altas e Inserciones de Sistema</p>", unsafe_allow_html=True)
    col_f_sup, col_f_ope, col_f_cis = st.columns(3)
    
    with col_f_sup:
        st.markdown("<p style='color:#FF454B; font-weight:700; font-size:13px; margin-bottom:10px;'>👤 NUEVO SUPERVISOR</p>", unsafe_allow_html=True)
        with st.form("f_sup_add", clear_on_submit=True):
            s_name = st.text_input("Nombres Completos:", placeholder="Ej: ALVITRES FRANKLIN")
            s_user = st.text_input("Usuario Acceso:", placeholder="ej: f.alvitres")
            s_pass = st.text_input("Contraseña:", type="password", placeholder="••••••••")
            if st.form_submit_button("REGISTRAR SUPERVISOR", type="primary", use_container_width=True):
                if s_name and s_user and s_pass:
                    res = requests.post(f"{BACKEND_URL}/api/supervisors", json={"full_name": s_name, "username": s_user, "password": s_pass})
                    if res.status_code == 200: 
                        st.success("✅ Supervisor creado.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Error: {res.json().get('detail', 'No se pudo crear.')}")
                else: 
                    st.warning("Complete todos los campos.")

    with col_f_ope:
        st.markdown("<p style='color:#FF454B; font-weight:700; font-size:13px; margin-bottom:10px;'>👷 NUEVO OPERADOR</p>", unsafe_allow_html=True)
        with st.form("f_ope_add", clear_on_submit=True):
            o_name = st.text_input("Nombre del Conductor:", placeholder="Ej: DANNY CALATAYUD")
            st.markdown("<div style='height: 72px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("REGISTRAR OPERADOR", type="primary", use_container_width=True):
                if o_name.strip():
                    res = requests.post(f"{BACKEND_URL}/api/operators", json={"full_name": o_name})
                    if res.status_code == 200: 
                        st.success("✅ Operador creado.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Error: {res.json().get('detail')}")

    with col_f_cis:
        st.markdown("<p style='color:#FF454B; font-weight:700; font-size:13px; margin-bottom:10px;'>🚒 ALTA DE CISTERNA</p>", unsafe_allow_html=True)
        with st.form("f_cis_add", clear_on_submit=True):
            t_plate = st.text_input("Número de Placa:", placeholder="Ej: B2E-796")
            st.markdown("<div style='height: 72px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("REGISTRAR CISTERNA", type="primary", use_container_width=True):
                if t_plate.strip():
                    res = requests.post(f"{BACKEND_URL}/api/fuel-trucks", json={"license_plate": t_plate})
                    if res.status_code == 200: 
                        st.success("✅ Cisterna creada.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Error: {res.json().get('detail')}")

    st.markdown("<p class='section-title'>📋 Personal y Unidades Registradas en Ecosistema</p>", unsafe_allow_html=True)
    col_t_sup, col_t_ope, col_t_cis = st.columns(3)
    
    with col_t_sup:
        st.markdown("<div class='tabla-header-sm'>Supervisores de Campo</div>", unsafe_allow_html=True)
        for n, c in list(supervisor_display.items()):
            if n != "-":
                st.markdown(f"<div class='tabla-minimalista-fila'><span><code style='color:#FF454B; font-weight:600;'>{c}</code> &nbsp; {n}</span></div>", unsafe_allow_html=True)
                if st.button("Eliminar", key=f"ds_{c}", use_container_width=True, type="secondary"):
                    res = requests.delete(f"{BACKEND_URL}/api/supervisors/{c}")
                    if res.status_code == 200:
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ {res.json().get('detail', 'No se pudo eliminar.')}")

    with col_t_ope:
        st.markdown("<div class='tabla-header-sm'>Operadores Certificados</div>", unsafe_allow_html=True)
        for n, c in list(operator_display.items()):
            if n != "-":
                st.markdown(f"<div class='tabla-minimalista-fila'><span><code style='color:#FF454B; font-weight:600;'>{c}</code> &nbsp; {n}</span></div>", unsafe_allow_html=True)
                if st.button("Eliminar", key=f"do_{c}", use_container_width=True, type="secondary"):
                    res = requests.delete(f"{BACKEND_URL}/api/operators/{c}")
                    if res.status_code == 200:
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ {res.json().get('detail', 'No se pudo eliminar.')}")

    with col_t_cis:
        st.markdown("<div class='tabla-header-sm'>Flota de Cisternas</div>", unsafe_allow_html=True)
        for plate, c in list(truck_display.items()):
            if plate != "-":
                st.markdown(f"<div class='tabla-minimalista-fila'><span><code style='color:#FF454B; font-weight:600;'>{c}</code> &nbsp; <b>{plate}</b></span></div>", unsafe_allow_html=True)
                if st.button("Eliminar", key=f"dt_{c}", use_container_width=True, type="secondary"):
                    res = requests.delete(f"{BACKEND_URL}/api/fuel-trucks/{c}")
                    if res.status_code == 200:
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ {res.json().get('detail', 'No se pudo eliminar.')}")

# ===========================================================================
# MODULO: HISTORIAL Y DESCARGA DE REPORTES
# ===========================================================================
elif modulo_seleccionado == "📋 Historial y Reportes":
    st.markdown("<h2 class='main-header-title'>HISTORIAL GENERAL DE REPORTES</h2>", unsafe_allow_html=True)
    try: 
        res = requests.get(f"{BACKEND_URL}/api/fuel-logs-history", timeout=12.0)
        historial = res.json() if res.status_code == 200 else []
    except Exception: 
        historial = []

    if historial:
        df_hist = pd.DataFrame(historial)
        df_hist.columns = ["ID LOG", "FECHA", "GUARDIA", "COMBUSTIBLE", "SUPERVISOR", "OPERADOR", "PLACA CISTERNA", "OBSERVACIONES"]
        
        csv_data = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 DESCARGAR HISTORIAL EN CSV (EXCEL)",
            data=csv_data,
            file_name=f"reporte_combustible_jex_{datetime.date.today()}.csv",
            mime="text/csv",
            type="primary"
        )
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else: 
        st.info("No se registran hojas de control operativo almacenadas en la base de datos.")