"""
Panel de Administracion - CV Generator App.

Aplicacion Streamlit independiente para gestion de usuarios, tokens y auditoria.
Ejecutar: streamlit run admin_app.py --server.port 8502
"""

import streamlit as st
import time

from src.logger import get_logger
from src.auth import AuthManager
from src.token_tracker import TokenTracker, USER_LIMIT_COP

logger = get_logger("admin")

# Configuracion de pagina
st.set_page_config(
    page_title="Admin - CV Generator",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Autenticacion Admin
# ============================================================

if "admin_user" not in st.session_state:
    st.session_state.admin_user = None

if "admin_selected_user" not in st.session_state:
    st.session_state.admin_selected_user = None


def _show_admin_login() -> bool:
    """Muestra login y verifica que el usuario sea admin."""
    if st.session_state.admin_user is not None:
        return True

    st.markdown(
        '<h1 style="text-align:center;">🔧 Panel de Administracion</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center;color:#666;">Solo administradores</p>',
        unsafe_allow_html=True,
    )

    col_l, col_form, col_r = st.columns([1, 2, 1])
    with col_form:
        st.subheader("Iniciar Sesion")
        with st.form("admin_login"):
            email = st.text_input("Email", placeholder="admin@example.com")
            password = st.text_input("Contrasena", type="password")
            submitted = st.form_submit_button("Ingresar", type="primary", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Ingresa email y contrasena.")
                return False
            try:
                auth = AuthManager()
                result = auth.sign_in(email, password)
                if result.success and result.user:
                    user_id = result.user["id"]
                    if auth.is_admin(user_id):
                        st.session_state.admin_user = result.user
                        st.rerun()
                    else:
                        st.error("Acceso denegado. Solo administradores.")
                else:
                    st.error(result.error or "Credenciales invalidas.")
            except Exception as e:
                st.error(f"Error de conexion: {e}")

    return False


if not _show_admin_login():
    st.stop()

# ============================================================
# Admin autenticado - Panel principal
# ============================================================

admin_id = st.session_state.admin_user["id"]
admin_email = st.session_state.admin_user.get("email", "")

# Sidebar
with st.sidebar:
    st.caption(f"🔧 Admin: {admin_email}")
    if st.button("🚪 Cerrar Sesion", use_container_width=True):
        st.session_state.admin_user = None
        st.session_state.admin_selected_user = None
        st.rerun()
    st.divider()

    nav = st.radio(
        "Navegacion",
        ["👥 Usuarios", "📊 Detalle Usuario", "📜 Log de Auditoria"],
        label_visibility="collapsed",
    )

# Inicializar servicios
auth = AuthManager()
tracker = TokenTracker()

# ============================================================
# Metricas globales
# ============================================================

st.title("🔧 Panel de Administracion")

# Cargar datos
all_profiles = auth.get_all_profiles()
all_usage = tracker.get_all_users_usage()
usage_map = {u["user_id"]: u for u in all_usage}

# Metricas
total_users = len(all_profiles)
active_users = sum(1 for p in all_profiles if p.get("is_active", True))
total_cost = sum(u["total_cost_cop"] for u in all_usage)
blocked_users = sum(
    1 for p in all_profiles if usage_map.get(p["id"], {}).get("total_cost_cop", 0) >= USER_LIMIT_COP
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Usuarios", total_users)
col2.metric("Activos", active_users)
col3.metric("Bloqueados (limite)", blocked_users)
col4.metric("Costo Total Plataforma", f"${total_cost:,.2f} COP")

st.divider()

# ============================================================
# Tab: Lista de Usuarios (US-TK-007)
# ============================================================

if nav == "👥 Usuarios":
    st.header("👥 Gestion de Usuarios")

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        status_filter = st.selectbox("Estado", ["Todos", "Activos", "Inactivos"])
    with col_f2:
        role_filter = st.selectbox("Rol", ["Todos", "user", "admin"])

    # Filtrar
    filtered = all_profiles
    if status_filter == "Activos":
        filtered = [p for p in filtered if p.get("is_active", True)]
    elif status_filter == "Inactivos":
        filtered = [p for p in filtered if not p.get("is_active", True)]

    if role_filter != "Todos":
        filtered = [p for p in filtered if p.get("role") == role_filter]

    if not filtered:
        st.info("No hay usuarios con esos filtros.")
    else:
        for profile in filtered:
            uid = profile["id"]
            email = profile.get("email", uid[:8])
            role = profile.get("role", "user")
            is_active = profile.get("is_active", True)
            created = str(profile.get("created_at", ""))[:10]
            usage = usage_map.get(uid, {})
            cost = usage.get("total_cost_cop", 0.0)
            is_over_limit = cost >= USER_LIMIT_COP

            # Row
            cols = st.columns([3, 1, 1, 2, 2])
            cols[0].write(f"**{email}**")
            cols[1].write(f"`{role}`")
            if is_active:
                cols[2].write("🟢 Activo")
            else:
                cols[2].write("🔴 Inactivo")
            cols[3].write(f"${cost:,.2f} COP")

            with cols[4]:
                btn_cols = st.columns(2)
                # Ver detalle
                if btn_cols[0].button("📊", key=f"detail_{uid}", help="Ver detalle"):
                    st.session_state.admin_selected_user = uid
                    st.rerun()

                # Activar / Desactivar
                if is_active:
                    if btn_cols[1].button("🔴", key=f"deact_{uid}", help="Desactivar"):
                        st.session_state[f"confirm_deact_{uid}"] = True
                        st.rerun()
                else:
                    if btn_cols[1].button("🟢", key=f"act_{uid}", help="Activar"):
                        st.session_state[f"confirm_act_{uid}"] = True
                        st.rerun()

            # Confirmaciones
            if st.session_state.get(f"confirm_deact_{uid}"):
                with st.container():
                    st.warning(f"Desactivar a **{email}**?")
                    notes = st.text_input("Notas (opcional)", key=f"notes_deact_{uid}")
                    c1, c2 = st.columns(2)
                    if c1.button("Confirmar", key=f"yes_deact_{uid}", type="primary"):
                        auth.set_user_active(uid, False)
                        total_input = usage.get("total_input_tokens", 0)
                        total_output = usage.get("total_output_tokens", 0)
                        tracker.log_audit_action(
                            user_id=uid,
                            admin_id=admin_id,
                            action="deactivate",
                            tokens_at_action=total_input + total_output,
                            cost_at_action_cop=cost,
                            notes=notes or None,
                        )
                        del st.session_state[f"confirm_deact_{uid}"]
                        st.success(f"Usuario {email} desactivado.")
                        time.sleep(1)
                        st.rerun()
                    if c2.button("Cancelar", key=f"no_deact_{uid}"):
                        del st.session_state[f"confirm_deact_{uid}"]
                        st.rerun()

            if st.session_state.get(f"confirm_act_{uid}"):
                with st.container():
                    st.warning(f"Activar a **{email}**? Se reseteara su consumo de tokens.")
                    notes = st.text_input("Notas (opcional)", key=f"notes_act_{uid}")
                    c1, c2 = st.columns(2)
                    if c1.button("Confirmar", key=f"yes_act_{uid}", type="primary"):
                        total_input = usage.get("total_input_tokens", 0)
                        total_output = usage.get("total_output_tokens", 0)
                        tracker.log_audit_action(
                            user_id=uid,
                            admin_id=admin_id,
                            action="activate",
                            tokens_at_action=total_input + total_output,
                            cost_at_action_cop=cost,
                            notes=notes or None,
                        )
                        tracker.reset_user_tokens(uid)
                        auth.set_user_active(uid, True)
                        del st.session_state[f"confirm_act_{uid}"]
                        st.success(f"Usuario {email} activado. Tokens reseteados.")
                        time.sleep(1)
                        st.rerun()
                    if c2.button("Cancelar", key=f"no_act_{uid}"):
                        del st.session_state[f"confirm_act_{uid}"]
                        st.rerun()

            st.divider()

# ============================================================
# Tab: Detalle de Usuario (US-TK-009)
# ============================================================

elif nav == "📊 Detalle Usuario":
    st.header("📊 Detalle de Usuario")

    selected_uid = st.session_state.admin_selected_user

    if not selected_uid:
        # Selector de usuario
        user_options = {p.get("email", p["id"][:8]): p["id"] for p in all_profiles}
        if not user_options:
            st.info("No hay usuarios registrados.")
            st.stop()

        selected_email = st.selectbox("Seleccionar usuario", list(user_options.keys()))
        if selected_email:
            selected_uid = user_options[selected_email]

    if selected_uid:
        profile = auth.get_user_profile(selected_uid)
        if not profile:
            st.error("Perfil no encontrado.")
            st.stop()

        # Perfil
        st.subheader(f"👤 {profile.get('email', selected_uid[:8])}")
        p_cols = st.columns(4)
        p_cols[0].metric("Rol", profile.get("role", "user"))
        p_cols[1].metric("Estado", "Activo" if profile.get("is_active", True) else "Inactivo")
        p_cols[2].metric("Registro", str(profile.get("created_at", ""))[:10])

        usage = usage_map.get(selected_uid, {})
        total_cost_user = usage.get("total_cost_cop", 0.0)
        p_cols[3].metric("Costo Total", f"${total_cost_user:,.2f} COP")

        st.divider()

        # Consumo por CV
        st.subheader("📁 Consumo por Hoja de Vida")
        cv_summaries = tracker.get_usage_summary_by_cv(selected_uid)
        if cv_summaries:
            for s in cv_summaries:
                with st.expander(
                    f"{s.job_title} — {s.operations_count} ops, ${s.total_cost_cop:,.2f} COP"
                ):
                    st.write(f"**Input tokens:** {s.total_input_tokens:,}")
                    st.write(f"**Output tokens:** {s.total_output_tokens:,}")
                    if s.last_used:
                        st.write(f"**Ultimo uso:** {s.last_used[:16]}")
                    if s.cv_id:
                        records = tracker.get_usage_by_cv(selected_uid, s.cv_id)
                        if records:
                            st.caption("Operaciones:")
                            for r in records:
                                st.caption(
                                    f"  `{r.operation}` — in:{r.input_tokens} out:{r.output_tokens} "
                                    f"${r.total_cost_cop:,.4f} ({r.created_at[:16] if r.created_at else 'N/A'})"
                                )
        else:
            st.info("Sin consumo registrado.")

        st.divider()

        # Historial de operaciones
        st.subheader("📜 Historial de Operaciones")
        history = tracker.get_usage_history(selected_uid, limit=50)
        if history:
            for r in history:
                date_label = r.created_at[:16] if r.created_at else "N/A"
                st.caption(
                    f"`{r.operation}` — in:{r.input_tokens:,} out:{r.output_tokens:,} "
                    f"${r.total_cost_cop:,.4f} COP — {r.model_used} ({date_label})"
                )
        else:
            st.info("Sin historial.")

        st.divider()

        # Auditoria del usuario
        st.subheader("🔍 Log de Auditoria")
        audit = tracker.get_audit_log(user_id=selected_uid)
        if audit:
            for entry in audit:
                action_icon = "🟢" if entry["action"] == "activate" else "🔴"
                date_label = str(entry.get("created_at", ""))[:16]
                st.caption(
                    f"{action_icon} **{entry['action'].upper()}** — "
                    f"Admin: {entry.get('admin_id', 'N/A')[:8]}... — "
                    f"Tokens: {entry.get('tokens_at_action', 0):,} — "
                    f"${entry.get('cost_at_action_cop', 0):,.2f} COP — "
                    f"{date_label}"
                )
                if entry.get("notes"):
                    st.caption(f"  📝 {entry['notes']}")
        else:
            st.info("Sin log de auditoria para este usuario.")

        # Acciones
        st.divider()
        is_active = profile.get("is_active", True)
        if is_active:
            if st.button("🔴 Desactivar Usuario", type="secondary"):
                notes = st.text_input("Notas (opcional)", key="detail_deact_notes")
                auth.set_user_active(selected_uid, False)
                tracker.log_audit_action(
                    user_id=selected_uid,
                    admin_id=admin_id,
                    action="deactivate",
                    tokens_at_action=usage.get("total_input_tokens", 0)
                    + usage.get("total_output_tokens", 0),
                    cost_at_action_cop=total_cost_user,
                    notes=notes or None,
                )
                st.success("Usuario desactivado.")
                time.sleep(1)
                st.rerun()
        else:
            if st.button("🟢 Activar Usuario", type="primary"):
                notes = st.text_input("Notas (opcional)", key="detail_act_notes")
                tracker.log_audit_action(
                    user_id=selected_uid,
                    admin_id=admin_id,
                    action="activate",
                    tokens_at_action=usage.get("total_input_tokens", 0)
                    + usage.get("total_output_tokens", 0),
                    cost_at_action_cop=total_cost_user,
                    notes=notes or None,
                )
                tracker.reset_user_tokens(selected_uid)
                auth.set_user_active(selected_uid, True)
                st.success("Usuario activado. Tokens reseteados.")
                time.sleep(1)
                st.rerun()

# ============================================================
# Tab: Log de Auditoria (US-TK-008)
# ============================================================

elif nav == "📜 Log de Auditoria":
    st.header("📜 Log de Auditoria")

    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        user_filter_options = ["Todos"] + [p.get("email", p["id"][:8]) for p in all_profiles]
        user_filter = st.selectbox("Usuario", user_filter_options)
    with col_f2:
        action_filter = st.selectbox("Accion", ["Todas", "activate", "deactivate"])

    # Obtener user_id del filtro
    filter_uid = None
    if user_filter != "Todos":
        for p in all_profiles:
            if p.get("email", p["id"][:8]) == user_filter:
                filter_uid = p["id"]
                break

    action_f = action_filter if action_filter != "Todas" else None

    audit_log = tracker.get_audit_log(user_id=filter_uid, action_filter=action_f, limit=100)

    if not audit_log:
        st.info("No hay registros de auditoria.")
    else:
        # Crear tabla con email lookup
        email_map = {p["id"]: p.get("email", p["id"][:8]) for p in all_profiles}

        for entry in audit_log:
            action_icon = "🟢" if entry["action"] == "activate" else "🔴"
            date_label = str(entry.get("created_at", ""))[:16]
            user_email = email_map.get(entry["user_id"], entry["user_id"][:8])
            admin_email_val = email_map.get(
                entry.get("admin_id", ""), entry.get("admin_id", "")[:8]
            )

            with st.container():
                cols = st.columns([2, 2, 1, 2, 2, 2])
                cols[0].write(f"📅 {date_label}")
                cols[1].write(f"👤 {user_email}")
                cols[2].write(f"{action_icon} {entry['action']}")
                cols[3].write(f"🔧 {admin_email_val}")
                cols[4].write(f"Tokens: {entry.get('tokens_at_action', 0):,}")
                cols[5].write(f"${entry.get('cost_at_action_cop', 0):,.2f} COP")

                if entry.get("notes"):
                    st.caption(f"  📝 {entry['notes']}")
                st.divider()
