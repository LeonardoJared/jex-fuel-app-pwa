import streamlit as st
import requests
import datetime
import os
import pandas as pd
import base64

# ===========================================================================
# CONFIGURACIÓN Y RUTAS RELATIVAS SEGURAS
# ===========================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(CURRENT_DIR, "assets")
CSS_FILE = os.path.join(CURRENT_DIR, "styles.css")
ICON_FILE = os.path.join(ASSETS_DIR, "logo_jex.ico")
LOGO_FILE = os.path.join(ASSETS_DIR, "logo_jex.png")

st.set_page_config(
    page_title="JEX Technologies - Admin", 
    page_icon=ICON_FILE if os.path.exists(ICON_FILE) else "⛽",
    layout="wide", 
    initial_sidebar_state="expanded"
)

def load_css(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(CSS_FILE)

# Variables de sesión
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "modulo_seleccionado" not in st.session_state:
    st.session_state.modulo_seleccionado = "📊 DASHBOARD"

BACKEND_URL = os.getenv("JEX_BACKEND_URL", "http://localhost:8000")

# ===========================================================================
# PANTALLA DE LOGIN
# ===========================================================================
if not st.session_state.logged_in:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    _, col_login_box, _ = st.columns([2.3, 1.2, 2.3])
    
    with col_login_box:
        if os.path.exists(LOGO_FILE):
            with open(LOGO_FILE, "rb") as img_file:
                encoded_logo = base64.b64encode(img_file.read()).decode()
            st.markdown(
                f"<div class='sidebar-logo-box'>"
                f"<img src='data:image/png;base64,{encoded_logo}' class='sidebar-logo-img'>"
                f"<div class='sidebar-logo-sub'>CONTROL DE COMBUSTIBLE</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        st.markdown("<h3 class='main-header-title' style='text-align: center;'>LOGIN</h3>", unsafe_allow_html=True)
        
        username_input = st.text_input("USUARIO:")
        password_input = st.text_input("CONTRASEÑA:", type="password")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        submit_login = st.button("INGRESAR", type="primary", use_container_width=True)
        
        if submit_login:
            if username_input and password_input:
                try:
                    res = requests.post(f"{BACKEND_URL}/api/login", json={
                        "username": username_input.strip(),
                        "password": password_input.strip()
                    }, timeout=15.0)
                    
                    if res.status_code == 200:
                        data = res.json()
                        rol_usuario = str(data.get("role", "")).upper()

                        if rol_usuario not in ["ADMIN", "ADMINISTRADOR"]:
                            st.error("⛔ ACCESO DENEGADO: Panel exclusivo para el Administrador.")
                            st.stop()

                        st.session_state.logged_in = True
                        st.session_state.user_role = rol_usuario
                        st.session_state.user_name = data.get("name", "Administrador Central JEX")
                        st.rerun()
                    else:
                        st.error(f"❌ {res.json().get('detail', 'Credenciales incorrectas.')}")
                except Exception as e:
                    st.error(f"📡 Error de comunicación con el backend: {e}")
            else:
                st.warning("⚠️ Complete todos los campos.")
    st.stop()

if st.session_state.logged_in and st.session_state.user_role not in ["ADMIN", "ADMINISTRADOR"]:
    st.error("⛔ ACCESO DENEGADO: Panel exclusivo para el Administrador.")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_name = None
        st.rerun()
    st.stop()

# ===========================================================================
# CONSULTAS DE CATÁLOGOS CON CACHÉ
# ===========================================================================
@st.cache_data(ttl=60)
def obtener_supervisores():
    try: return requests.get(f"{BACKEND_URL}/api/supervisors", timeout=8.0).json()
    except Exception: return []

@st.cache_data(ttl=60)
def obtener_operadores():
    try: return requests.get(f"{BACKEND_URL}/api/operators", timeout=8.0).json()
    except Exception: return []

@st.cache_data(ttl=60)
def obtener_cisternas():
    try: return requests.get(f"{BACKEND_URL}/api/fuel-trucks", timeout=8.0).json()
    except Exception: return []

@st.cache_data(ttl=60)
def obtener_combustibles():
    try: return requests.get(f"{BACKEND_URL}/api/fuel-types", timeout=8.0).json()
    except Exception: return []

supervisores = obtener_supervisores()
operadores = obtener_operadores()
cisternas = obtener_cisternas()
combustibles = obtener_combustibles()

# ===========================================================================
# BARRA LATERAL
# ===========================================================================

if os.path.exists(LOGO_FILE):
    with open(LOGO_FILE, "rb") as img_f:
        encoded_logo = base64.b64encode(img_f.read()).decode()
    st.sidebar.markdown(
        f"""
        <div class="sidebar-logo-box">
            <img src="data:image/png;base64,{encoded_logo}" class="sidebar-logo-img">
            <div class="sidebar-logo-sub">CONTROL DE COMBUSTIBLE</div>
        </div>
        """,
        unsafe_allow_html=True
    )

foto_admin = os.path.join(ASSETS_DIR, "foto_perfil.png")
if os.path.exists(foto_admin):
    with open(foto_admin, "rb") as img_f:
        encoded_foto = base64.b64encode(img_f.read()).decode()
    st.sidebar.markdown(
        f"""
        <div class="admin-photo-container">
            <div class="admin-circle-frame">
                <img src="data:image/png;base64,{encoded_foto}" class="admin-photo-img">
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

nombre_admin_mostrar = st.session_state.user_name or "Administrador Central JEX"
st.sidebar.markdown(f"<div class='admin-name-text'>{nombre_admin_mostrar}</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='admin-role-badge'>A D M I N I S T R A D O R</div>", unsafe_allow_html=True)

st.sidebar.markdown("<hr style='border-color: #1A2438; margin: 8px 0 14px 0;'>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color:#64748B; font-size:11px; font-weight:800; letter-spacing:0.8px; margin-bottom:8px; text-transform:uppercase;'>MENÚ DE GESTIÓN:</p>", unsafe_allow_html=True)

modulos_disponibles = [
    "📊 DASHBOARD",
    "👤 SUPERVISORES",
    "👷 OPERADORES",
    "🚒 CISTERNAS",
    "📋 REPORTES",
    "⚙️ CONFIGURACIÓN",
]

for mod in modulos_disponibles:
    if st.session_state.modulo_seleccionado == mod:
        st.sidebar.markdown(f'<div class="active-nav-card">{mod}</div>', unsafe_allow_html=True)
    else:
        if st.sidebar.button(mod, key=f"nav_{mod}", use_container_width=True, type="secondary"):
            st.session_state.modulo_seleccionado = mod
            st.rerun()

st.sidebar.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

if st.sidebar.button("🔒 CERRAR SESIÓN", use_container_width=True, type="primary"):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.user_name = None
    st.rerun()

modulo_activo = st.session_state.modulo_seleccionado

# ===========================================================================
# 1. MÓDULO: 📊 DASHBOARD
# ===========================================================================
if modulo_activo == "📊 DASHBOARD":
    st.markdown("<h2 class='main-header-title'>MONITOREO OPERATIVO EN TIEMPO REAL</h2>", unsafe_allow_html=True)
    
    try: 
        res = requests.get(f"{BACKEND_URL}/api/fuel-logs-history", timeout=10.0)
        historial = res.json() if res.status_code == 200 else []
    except Exception: 
        historial = []

    total_galones = sum(item.get('total_gln', 0.0) for item in historial)

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("VOLUMEN HISTÓRICO", f"{total_galones:,.1f} GLN")
    kpi2.metric("TOTAL REPORTES", f"{len(historial)}")
    kpi3.metric("SUPERVISORES", f"{len(supervisores)}")
    kpi4.metric("OPERADORES", f"{len(operadores)}")
    kpi5.metric("CISTERNAS", f"{len(cisternas)}")

    st.markdown("<p class='section-title'>Últimas Transacciones Registradas</p>", unsafe_allow_html=True)
    if historial:
        df_dash = pd.DataFrame(historial)[["log_id", "log_date", "shift", "fuel_type", "supervisor", "operator", "truck_plate", "total_gln", "remarks"]]
        df_dash.columns = ["ID", "FECHA", "GUARDIA", "COMBUSTIBLE", "SUPERVISOR", "OPERADOR", "CISTERNA", "TOTAL GLN", "OBSERVACIONES"]
        st.dataframe(df_dash.head(10), use_container_width=True, hide_index=True)
    else:
        st.info("No se registran datos transaccionales en la plataforma.")

# ===========================================================================
# 2. MÓDULO: 👤 SUPERVISORES
# ===========================================================================
elif modulo_activo == "👤 SUPERVISORES":
    st.markdown("<h2 class='main-header-title'>GESTIÓN DE SUPERVISORES DE CAMPO</h2>", unsafe_allow_html=True)

    dialog_decorator = getattr(st, "dialog", getattr(st, "experimental_dialog", None))

    # Mostrar notificaciones pendientes de acciones anteriores fuera de la tabla
    if "notif_admin" in st.session_state and st.session_state.notif_admin:
        tipo, msg = st.session_state.notif_admin
        if tipo == "success":
            st.toast(msg, icon="✅")
        elif tipo == "error":
            st.toast(msg, icon="❌")
        st.session_state.notif_admin = None

    # -----------------------------------------------------------------------
    # MODAL 1: REGISTRAR NUEVO SUPERVISOR
    # -----------------------------------------------------------------------
    if dialog_decorator:
        @dialog_decorator("➕ Registrar Nuevo Supervisor")
        def modal_crear_supervisor():
            with st.form("form_modal_crear_sup", clear_on_submit=False):
                new_name = st.text_input("Nombres y Apellidos Completos:", placeholder="Ej: CARLOS MENDOZA")
                new_user = st.text_input("Usuario de Acceso PWA:", placeholder="ej: c.mendoza")
                new_pass = st.text_input("Contraseña Inicial:", type="password", placeholder="••••••••")
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                c_save, c_cancel = st.columns(2)
                with c_save:
                    btn_crear = st.form_submit_button("GUARDAR EN NEON", type="primary", use_container_width=True)
                with c_cancel:
                    btn_cancel = st.form_submit_button("CANCELAR", use_container_width=True)

                if btn_crear:
                    if new_name.strip() and new_user.strip() and new_pass.strip():
                        res = requests.post(f"{BACKEND_URL}/api/supervisors", json={
                            "full_name": new_name.strip(),
                            "username": new_user.strip(),
                            "password": new_pass.strip()
                        })
                        if res.status_code == 200:
                            st.session_state.notif_admin = ("success", f"Supervisor {new_name.strip().upper()} creado exitosamente.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            # ✅ Mensaje limpio sin código SQL
                            err_msg = res.json().get('detail', 'No se pudo crear el supervisor.')
                            st.warning(f"⚠️ {err_msg}")
                    else:
                        st.warning("⚠️ Complete todos los campos.")
                
                if btn_cancel:
                    st.rerun()

        # -------------------------------------------------------------------
        # MODAL 2: EDITAR SUPERVISOR
        # -------------------------------------------------------------------
        @dialog_decorator("✏️ Editar Supervisor")
        def modal_editar_supervisor(sup):
            st.markdown(f"**Modificando:** <code style='color:#E8B828;'>{sup['id']}</code> — **{sup['name']}**", unsafe_allow_html=True)
            with st.form("form_modal_edit_sup"):
                e_name = st.text_input("Nombres y Apellidos:", value=sup['name'])
                e_user = st.text_input("Usuario PWA:", value=sup.get('username', ''))
                e_pass = st.text_input("Resetear Contraseña (opcional):", type="password", placeholder="Dejar en blanco para mantener actual")
                e_active = st.selectbox("Estado de Acceso:", ["ACTIVO", "INACTIVO"], index=0 if sup.get('is_active', True) else 1)
                
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                b_save, b_cancel = st.columns(2)
                with b_save:
                    btn_guardar = st.form_submit_button("💾 GUARDAR CAMBIOS", type="primary", use_container_width=True)
                with b_cancel:
                    btn_cancel_e = st.form_submit_button("CANCELAR", use_container_width=True)

                if btn_guardar:
                    if e_name.strip() and e_user.strip():
                        res_up = requests.put(f"{BACKEND_URL}/api/supervisors/{sup['id']}", json={
                            "full_name": e_name.strip(),
                            "username": e_user.strip(),
                            "password": e_pass.strip() if e_pass.strip() else None,
                            "is_active": (e_active == "ACTIVO")
                        })
                        if res_up.status_code == 200:
                            st.session_state.notif_admin = ("success", f"Supervisor {sup['id']} actualizado correctamente.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.warning(f"⚠️ {res_up.json().get('detail', 'Error al actualizar.')}")
                    else:
                        st.warning("⚠️ Nombre y usuario no pueden estar vacíos.")

                if btn_cancel_e:
                    st.rerun()

        # -------------------------------------------------------------------
        # MODAL 3: CONFIRMAR ELIMINACIÓN
        # -------------------------------------------------------------------
        @dialog_decorator("⚠️ Confirmar Baja de Supervisor")
        def modal_confirmar_baja(sup):
            st.markdown(
                f"""
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 14px; margin-bottom: 14px;">
                    <span style="color: #EF4444; font-weight: 800; font-size: 14px;">¿Está seguro de eliminar a este supervisor?</span><br>
                    <span style="color: #FFFFFF; font-size: 13px;"><b>{sup['name']}</b> (<code style="color:#E8B828;">{sup['id']}</code>)</span><br>
                    <span style="color: #94A3B8; font-size: 12px; margin-top: 4px; display: block;">Esta acción revocará su acceso a la PWA móvil de inmediato.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            c_del_yes, c_del_no = st.columns(2)
            with c_del_yes:
                if st.button("🗑️ SÍ, ELIMINAR", key=f"conf_del_{sup['id']}", type="primary", use_container_width=True):
                    res_del = requests.delete(f"{BACKEND_URL}/api/supervisors/{sup['id']}")
                    if res_del.status_code == 200:
                        st.session_state.notif_admin = ("success", f"Supervisor {sup['id']} eliminado del sistema.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        err_del = res_del.json().get('detail', 'No se pudo eliminar.')
                        st.session_state.notif_admin = ("error", f"No se pudo eliminar: {err_del}")
                        st.rerun()
            with c_del_no:
                if st.button("CANCELAR", key=f"canc_del_{sup['id']}", use_container_width=True):
                    st.rerun()

    total_sups = len(supervisores)
    sups_activos = sum(1 for s in supervisores if s.get("is_active", True))
    sups_inactivos = total_sups - sups_activos

    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL SUPERVISORES", f"{total_sups}")
    m2.metric("ACTIVOS EN CAMPO", f"{sups_activos}")
    m3.metric("INACTIVOS / BLOQUEADOS", f"{sups_inactivos}")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 2. BARRA DE HERRAMIENTAS
    col_search, col_btn_nuevo = st.columns([3.5, 1.2])
    
    with col_search:
        filtro = st.text_input("🔍 Buscar:", placeholder="Filtrar por nombre, código SUP o usuario...", label_visibility="collapsed").strip().lower()
    
    with col_btn_nuevo:
        if st.button("➕ NUEVO SUPERVISOR", type="primary", use_container_width=True):
            if dialog_decorator:
                modal_crear_supervisor()

    # 3. FILTRADO
    sups_filtrados = [
        s for s in supervisores 
        if filtro in s['name'].lower() 
        or filtro in s['id'].lower() 
        or filtro in s.get('username', '').lower()
    ] if filtro else supervisores

    # 4. TABLA DE DATOS
    PROPORCION_TABLA = [1.0, 3.8, 2.2, 1.4, 1.6]

    h1, h2, h3, h4, h5 = st.columns(PROPORCION_TABLA)
    h1.markdown("<span class='th-text'>CÓDIGO</span>", unsafe_allow_html=True)
    h2.markdown("<span class='th-text'>NOMBRE COMPLETO</span>", unsafe_allow_html=True)
    h3.markdown("<span class='th-text'>USUARIO PWA</span>", unsafe_allow_html=True)
    h4.markdown("<span class='th-text'>ESTADO</span>", unsafe_allow_html=True)
    h5.markdown("<span class='th-text' style='float:right;'>ACCIONES</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 4px 0 10px 0; border-color: #1F2D47;'>", unsafe_allow_html=True)

    if sups_filtrados:
        for s in sups_filtrados:
            c_id, c_name, c_user, c_stat, c_acts = st.columns(PROPORCION_TABLA)

            with c_id:
                st.markdown(f"<span class='badge-code'>{s['id']}</span>", unsafe_allow_html=True)
            with c_name:
                st.markdown(f"<span style='color:#FFFFFF; font-weight:700; font-size:14px;'>{s['name']}</span>", unsafe_allow_html=True)
            with c_user:
                st.markdown(f"<span style='color:#94A3B8; font-size:13px;'>@{s.get('username', 'sin_usuario')}</span>", unsafe_allow_html=True)
            with c_stat:
                if s.get("is_active", True):
                    st.markdown("<span class='badge-status-active'>● ACTIVO</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span class='badge-status-inactive'>● INACTIVO</span>", unsafe_allow_html=True)
            with c_acts:
                col_btn_e, col_btn_d = st.columns([1, 1])
                with col_btn_e:
                    if st.button("✏️", key=f"e_{s['id']}", help="Editar supervisor", use_container_width=True, type="secondary"):
                        if dialog_decorator:
                            modal_editar_supervisor(s)
                with col_btn_d:
                    # ✅ Abre el modal de confirmación antes de eliminar
                    if st.button("🗑️", key=f"d_{s['id']}", help="Dar de baja", use_container_width=True, type="secondary"):
                        if dialog_decorator:
                            modal_confirmar_baja(s)
            
            st.markdown("<hr style='margin: 4px 0; border-color: #162032;'>", unsafe_allow_html=True)
    else:
        st.info("No se encontraron supervisores coincidentes con la búsqueda.")

# ===========================================================================
# 3. MÓDULO: 👷 OPERADORES
# ===========================================================================
elif modulo_activo == "👷 OPERADORES":
    st.markdown("<h2 class='main-header-title'>GESTIÓN DE OPERADORES DE CISTERNA</h2>", unsafe_allow_html=True)
    
    col_add_ope, col_list_ope = st.columns([1, 1.8])
    
    with col_add_ope:
        st.markdown("<p class='section-title'>Nuevo Operador</p>", unsafe_allow_html=True)
        with st.form("form_add_ope", clear_on_submit=True):
            o_name = st.text_input("Nombre Completo:", placeholder="Ej: DIMAS MAMANI")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("REGISTRAR OPERADOR", type="primary", use_container_width=True):
                if o_name.strip():
                    res = requests.post(f"{BACKEND_URL}/api/operators", json={"full_name": o_name})
                    if res.status_code == 200:
                        st.success("✅ Operador registrado.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(res.json().get('detail'))
                else:
                    st.warning("⚠️ Ingrese el nombre del conductor.")

    with col_list_ope:
        st.markdown("<p class='section-title'>Operadores Activos</p>", unsafe_allow_html=True)
        if operadores:
            for o in operadores:
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    st.markdown(f"<div class='tabla-minimalista-fila'><span><code style='color:#E8B828;'>{o['id']}</code> &nbsp; <b>{o['name']}</b></span></div>", unsafe_allow_html=True)
                with col_del:
                    if st.button("Eliminar", key=f"del_ope_{o['id']}", use_container_width=True, type="secondary"):
                        res = requests.delete(f"{BACKEND_URL}/api/operators/{o['id']}")
                        if res.status_code == 200:
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ {res.json().get('detail')}")
        else:
            st.info("No hay operadores registrados.")

# ===========================================================================
# 4. MÓDULO: 🚒 CISTERNAS
# ===========================================================================
elif modulo_activo == "🚒 CISTERNAS":
    st.markdown("<h2 class='main-header-title'>GESTIÓN DE FLOTA DE CISTERNAS</h2>", unsafe_allow_html=True)
    
    col_add_cis, col_list_cis = st.columns([1, 1.8])
    
    with col_add_cis:
        st.markdown("<p class='section-title'>Nueva Cisterna</p>", unsafe_allow_html=True)
        with st.form("form_add_cis", clear_on_submit=True):
            t_plate = st.text_input("Número de Placa:", placeholder="Ej: CAA-919")
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("REGISTRAR CISTERNA", type="primary", use_container_width=True):
                if t_plate.strip():
                    res = requests.post(f"{BACKEND_URL}/api/fuel-trucks", json={"license_plate": t_plate})
                    if res.status_code == 200:
                        st.success("✅ Cisterna agregada a la flota.")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(res.json().get('detail'))
                else:
                    st.warning("⚠️ Ingrese el número de placa.")

    with col_list_cis:
        st.markdown("<p class='section-title'>Cisternas Habilitadas</p>", unsafe_allow_html=True)
        if cisternas:
            for t in cisternas:
                col_info, col_del = st.columns([4, 1])
                with col_info:
                    st.markdown(f"<div class='tabla-minimalista-fila'><span><code style='color:#E8B828;'>{t['id']}</code> &nbsp; Placa: <b>{t['name']}</b></span></div>", unsafe_allow_html=True)
                with col_del:
                    if st.button("Eliminar", key=f"del_cis_{t['id']}", use_container_width=True, type="secondary"):
                        res = requests.delete(f"{BACKEND_URL}/api/fuel-trucks/{t['id']}")
                        if res.status_code == 200:
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"❌ {res.json().get('detail')}")
        else:
            st.info("No hay cisternas registradas.")

# ===========================================================================
# 5. MÓDULO: 📋 REPORTES (AUDITORÍA DE FIRMAS + EXPORTACIÓN EXCEL)
# ===========================================================================
elif modulo_activo == "📋 REPORTES":
    st.markdown("<h2 class='main-header-title'>AUDITORÍA DE REPORTES Y DESPACHOS</h2>", unsafe_allow_html=True)
    
    try: 
        res = requests.get(f"{BACKEND_URL}/api/fuel-logs-history", timeout=12.0)
        historial = res.json() if res.status_code == 200 else []
    except Exception: 
        historial = []

    if historial:
        df_full = pd.DataFrame(historial)[["log_id", "log_date", "shift", "fuel_type", "supervisor", "operator", "truck_plate", "total_gln", "remarks", "supervisor_signature", "operator_signature"]]
        
        # Filtros superiores
        col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
        with col_f1:
            fecha_ini = st.date_input("Desde:", datetime.date.today() - datetime.timedelta(days=30))
        with col_f2:
            fecha_fin = st.date_input("Hasta:", datetime.date.today())
        with col_f3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            df_export = df_full.drop(columns=["supervisor_signature", "operator_signature"])
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 EXPORTAR CSV / EXCEL",
                data=csv_data,
                file_name=f"reporte_jex_{datetime.date.today()}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )

        st.markdown("<p class='section-title'>Auditoría Detallada con Firmas Digitales</p>", unsafe_allow_html=True)
        
        opciones_rep = {
            f"ID #{r['log_id']} | {r['log_date']} | Guardia {r['shift']} | {r['supervisor']} ({r['total_gln']} GLN)": r 
            for r in historial
        }
        rep_sel = st.selectbox("SELECCIONE EL REPORTE A AUDITAR:", list(opciones_rep.keys()))
        rep = opciones_rep[rep_sel]

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**Fecha:** `{rep['log_date']}`  \n**Guardia:** `{rep['shift']}`")
        c2.markdown(f"**Supervisor:** `{rep['supervisor']}`  \n**Combustible:** `{rep['fuel_type']}`")
        c3.markdown(f"**Operador:** `{rep['operator']}`  \n**Cisterna:** `{rep['truck_plate']}`")
        c4.markdown(f"**Volumen Total:**  \n<h3 style='color:#E8B828; margin:0;'>{rep['total_gln']} GLN</h3>", unsafe_allow_html=True)

        st.info(f"📝 **Observaciones:** {rep['remarks']}")

        try:
            res_det = requests.get(f"{BACKEND_URL}/api/fuel-logs/{rep['log_id']}/details", timeout=8.0)
            detalles = res_det.json() if res_det.status_code == 200 else []
        except Exception:
            detalles = []

        if detalles:
            df_det = pd.DataFrame(detalles)
            df_det.columns = ["ITEM", "EQUIPO", "CÓDIGO INTERNO", "CANTIDAD (GLN)"]
            st.dataframe(df_det, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ Este reporte fue registrado sin despacho de combustible.")

        st.markdown("<p class='section-title'>Firmas de Validación Estampadas</p>", unsafe_allow_html=True)
        col_sig1, col_sig2 = st.columns(2)

        with col_sig1:
            st.markdown(f"**✍️ Firma del Supervisor:** `{rep['supervisor']}`")
            if rep.get('supervisor_signature'):
                st.image(rep['supervisor_signature'], width=340)
            else:
                st.caption("No registra firma.")

        with col_sig2:
            st.markdown(f"**✍️ Firma del Operador:** `{rep['operator']}`")
            if rep.get('operator_signature'):
                st.image(rep['operator_signature'], width=340)
            else:
                st.caption("No aplica (Guardia sin despacho).")

        st.markdown("<p class='section-title'>Tabla Completa de Historial</p>", unsafe_allow_html=True)
        st.dataframe(df_export, use_container_width=True, hide_index=True)
    else:
        st.info("No hay reportes registrados.")

# ===========================================================================
# 6. MÓDULO: ⚙️ CONFIGURACIÓN
# ===========================================================================
elif modulo_activo == "⚙️ CONFIGURACIÓN":
    st.markdown("<h2 class='main-header-title'>CONFIGURACIÓN DEL SISTEMA Y SEGURIDAD</h2>", unsafe_allow_html=True)
    
    col_cfg1, col_cfg2 = st.columns(2)
    
    with col_cfg1:
        st.markdown("<p class='section-title'>Perfil de Administrador</p>", unsafe_allow_html=True)
        st.markdown(f"**Usuario Actual:** `{st.session_state.user_name}`")
        st.markdown(f"**Rol:** `{st.session_state.user_role}`")
        st.markdown(f"**Algoritmo Criptográfico:** `Argon2id (OWASP Standard)`")
        st.markdown(f"**Base de Datos:** `PostgreSQL Cloud (Neon Serverless)`")

    with col_cfg2:
        st.markdown("<p class='section-title'>Estado del Servidor y Base de Datos</p>", unsafe_allow_html=True)
        try:
            res_health = requests.get(f"{BACKEND_URL}/health", timeout=5.0)
            if res_health.status_code == 200:
                st.success("🟢 API FastAPI y Neon PostgreSQL conectados y operando en línea.")
            else:
                st.error("🔴 Servidor o Base de Datos con advertencias.")
        except Exception as e:
            st.error(f"🔴 Sin conexión al backend: {e}")