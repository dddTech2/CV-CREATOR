"""
CV Generator App - Generador Inteligente de Hojas de Vida con IA
Frontend principal usando Streamlit
"""

import streamlit as st
import tempfile
import time
from pathlib import Path
import os
import concurrent.futures

from src.logger import get_logger

# Configurar logger
logger = get_logger("frontend")

# Importar módulos del backend
from src.cv_parser import CVParser
from src.job_analyzer import JobAnalyzer
from src.gap_analyzer import GapAnalyzer
from src.question_generator import QuestionGenerator, Language
from src.experience_rewriter import ExperienceRewriter
from src.yaml_generator import (
    YAMLGenerator,
    ContactInfo,
    ExperienceEntry,
    EducationEntry,
    SkillEntry,
)
from src.pdf_renderer import PDFRenderer
from src.database import CVDatabase
from src.ai_backend import GeminiClient
from src.prompts import PromptManager
from src.ai_proxy import InterviewProxy
from src.auth import AuthManager
from src.token_tracker import TokenTracker, USER_LIMIT_COP as TOKEN_TRACKER_LIMIT

# Configuración de la página
st.set_page_config(
    page_title="CV Generator - Estratega de Carrera con IA",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Autenticacion: Login / Registro
# ============================================================
# Inicializar estado de autenticacion
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None  # dict con id, email
if "auth_page" not in st.session_state:
    st.session_state.auth_page = "login"  # "login" o "register"


def _show_auth_page() -> bool:
    """Muestra la pagina de login/registro si no hay sesion activa.

    Returns:
        True si el usuario esta autenticado, False si no.
    """
    if st.session_state.auth_user is not None:
        # Verificar que el usuario sigue activo
        try:
            auth = AuthManager()
            user_id = st.session_state.auth_user["id"]
            if not auth.is_user_active(user_id):
                st.session_state.auth_user = None
                st.error("Tu cuenta ha sido desactivada. Contacta al administrador.")
                st.stop()
                return False
        except Exception:
            pass
        return True

    # --- Pagina de autenticacion ---
    st.markdown(
        '<h1 style="text-align:center;">📄 CV Generator con IA</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center;color:#666;">'
        "Inicia sesion o crea una cuenta para continuar</p>",
        unsafe_allow_html=True,
    )

    col_spacer_l, col_form, col_spacer_r = st.columns([1, 2, 1])

    with col_form:
        if st.session_state.auth_page == "login":
            _show_login_form()
        else:
            _show_register_form()

    return False


def _show_login_form() -> None:
    """Formulario de inicio de sesion."""
    st.subheader("Iniciar Sesion")
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="tu@email.com")
        password = st.text_input("Contrasena", type="password", placeholder="Min. 6 caracteres")
        submitted = st.form_submit_button(
            "Iniciar Sesion", type="primary", use_container_width=True
        )

    if submitted:
        if not email or not password:
            st.error("Ingresa tu email y contrasena.")
            return
        try:
            auth = AuthManager()
            result = auth.sign_in(email, password)
            if result.success and result.user:
                st.session_state.auth_user = result.user
                st.rerun()
            else:
                st.error(result.error or "Error al iniciar sesion.")
        except Exception as e:
            st.error(f"Error de conexion: {e}")

    if st.button("Crear cuenta nueva", use_container_width=True):
        st.session_state.auth_page = "register"
        st.rerun()


def _show_register_form() -> None:
    """Formulario de registro de usuario nuevo."""
    st.subheader("Crear Cuenta")
    with st.form("register_form"):
        email = st.text_input("Email", placeholder="tu@email.com")
        password = st.text_input("Contrasena", type="password", placeholder="Min. 8 caracteres")
        password_confirm = st.text_input("Confirmar Contrasena", type="password")
        submitted = st.form_submit_button("Crear Cuenta", type="primary", use_container_width=True)

    if submitted:
        # Validaciones client-side
        if not email or not password:
            st.error("Todos los campos son obligatorios.")
            return
        if len(password) < 8:
            st.error("La contrasena debe tener al menos 8 caracteres.")
            return
        if password != password_confirm:
            st.error("Las contrasenas no coinciden.")
            return

        try:
            auth = AuthManager()
            result = auth.sign_up(email, password)
            if result.success and result.user:
                st.session_state.auth_user = result.user
                st.success("Cuenta creada exitosamente.")
                time.sleep(1)
                st.rerun()
            else:
                st.error(result.error or "Error al crear la cuenta.")
        except Exception as e:
            st.error(f"Error de conexion: {e}")

    if st.button("Ya tengo cuenta", use_container_width=True):
        st.session_state.auth_page = "login"
        st.rerun()


# --- Verificar autenticacion ---
if not _show_auth_page():
    st.stop()


def _get_user_id() -> str:
    """Obtiene el user_id del usuario autenticado."""
    return st.session_state.auth_user["id"]


def _is_user_blocked() -> bool:
    """Verifica si el usuario excedio su limite de tokens."""
    try:
        tracker = TokenTracker()
        return tracker.is_user_blocked(_get_user_id())
    except Exception as e:
        logger.error(f"Error verificando limite de tokens: {e}")
        return False  # Ante error, permitir uso


def _record_token_usage(
    gemini_client: GeminiClient, operation: str, cv_id: int | None = None
) -> None:
    """Drena los tokens acumulados del GeminiClient y los registra en token_usage."""
    try:
        total_in, total_out = gemini_client.drain_usage()
        if total_in or total_out:
            tracker = TokenTracker()
            tracker.record_usage(
                user_id=_get_user_id(),
                operation=operation,
                input_tokens=total_in,
                output_tokens=total_out,
                cv_id=cv_id,
            )
    except Exception as e:
        logger.error(f"Error registrando token usage ({operation}): {e}")


# Inicializar session_state
if "cv_text" not in st.session_state:
    st.session_state.cv_text = ""
    # Intentar cargar CV Base por defecto
    try:
        db = CVDatabase()
        base_cv = db.get_base_cv(user_id=_get_user_id())
        if base_cv:
            st.session_state.cv_text = base_cv
            st.toast("ℹ️ Tu CV Base ha sido cargado automáticamente")
    except Exception as e:
        logger.error(f"Error cargando CV base: {e}")

if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "Español"
if "selected_theme" not in st.session_state:
    st.session_state.selected_theme = "classic"
if "gap_analysis_done" not in st.session_state:
    st.session_state.gap_analysis_done = False
if "gap_analysis_result" not in st.session_state:
    st.session_state.gap_analysis_result = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "generated_questions" not in st.session_state:
    st.session_state.generated_questions = []
if "current_question_index" not in st.session_state:
    st.session_state.current_question_index = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "questions_completed" not in st.session_state:
    st.session_state.questions_completed = False
if "prefilled_answers" not in st.session_state:
    st.session_state.prefilled_answers = {}
if "yaml_generated" not in st.session_state:
    st.session_state.yaml_generated = None
if "pdf_path" not in st.session_state:
    st.session_state.pdf_path = None

# NUEVO: Sistema de navegación automática por pasos
if "current_step" not in st.session_state:
    st.session_state.current_step = 0  # 0=Inputs, 1=Análisis, 2=Preguntas, 3=Resultado
if "last_uploaded_file_hash" not in st.session_state:
    st.session_state.last_uploaded_file_hash = None
if "auto_analysis_triggered" not in st.session_state:
    st.session_state.auto_analysis_triggered = False
if "auto_cv_generation_triggered" not in st.session_state:
    st.session_state.auto_cv_generation_triggered = False

# Estilos CSS personalizados
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0 2rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Header principal
st.markdown('<h1 class="main-header">📄 CV Generator con IA</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Tu estratega de carrera personal impulsado por Gemini AI</p>',
    unsafe_allow_html=True,
)

# NUEVO: Barra de progreso global
steps_names = ["📝 Inputs", "🔍 Análisis", "💬 Preguntas", "✅ Resultado", "🤖 Asistente"]
current_step_name = steps_names[st.session_state.current_step]
progress_value = (st.session_state.current_step + 1) / len(steps_names)

# Mostrar barra de progreso
st.progress(progress_value)

# Mostrar paso actual con emojis de completado y permitir navegación
progress_cols = st.columns(len(steps_names))
for idx, step_name in enumerate(steps_names):
    with progress_cols[idx]:
        # Determinar etiqueta y estilo
        if idx < st.session_state.current_step:
            label = f"✅ {step_name}"
            type_btn = "secondary"
        elif idx == st.session_state.current_step:
            label = f"🔵 {step_name}"
            type_btn = "primary"
        else:
            label = f"⚪ {step_name}"
            type_btn = "secondary"

        # Usar botones para navegación
        # Permitimos navegar a pasos anteriores o si ya se completó el flujo (ej. carga de CV)
        # O simplemente permitimos navegación libre (usuario pide "habilita la opción")
        if st.button(label, key=f"nav_step_{idx}", use_container_width=True, type=type_btn):
            st.session_state.current_step = idx
            st.rerun()

st.divider()

# Sidebar con historial
with st.sidebar:
    # --- Info de usuario y logout ---
    user_email = st.session_state.auth_user.get("email", "")
    st.caption(f"👤 {user_email}")
    if st.button("🚪 Cerrar Sesion", use_container_width=True, type="secondary"):
        try:
            auth_mgr = AuthManager()
            auth_mgr.sign_out()
        except Exception:
            pass
        st.session_state.auth_user = None
        # Limpiar estado de la app
        for key in list(st.session_state.keys()):
            if key not in ("auth_user", "auth_page"):
                del st.session_state[key]
        st.rerun()
    st.divider()

    # --- Consumo de tokens ---
    try:
        _tracker = TokenTracker()
        _user_total_cost = _tracker.get_user_total_cost(_get_user_id())
        _user_remaining = _tracker.get_user_remaining(_get_user_id())
        _usage_pct = (
            min(_user_total_cost / TOKEN_TRACKER_LIMIT * 100, 100) if TOKEN_TRACKER_LIMIT > 0 else 0
        )

        st.subheader("💰 Consumo IA")
        st.progress(
            min(_usage_pct / 100, 1.0),
            text=f"${_user_total_cost:,.1f} / ${TOKEN_TRACKER_LIMIT:,.0f} COP",
        )
        if _user_remaining <= 0:
            st.error("🚫 Limite alcanzado")
        elif _usage_pct >= 80:
            st.warning(f"⚠️ Quedan ${_user_remaining:,.1f} COP")
        else:
            st.caption(f"Restante: ${_user_remaining:,.1f} COP")

        with st.expander("📊 Detalle por CV"):
            _cv_summaries = _tracker.get_usage_summary_by_cv(_get_user_id())
            if _cv_summaries:
                for _s in _cv_summaries:
                    st.caption(
                        f"**{_s.job_title}** — {_s.operations_count} ops, "
                        f"${_s.total_cost_cop:,.2f} COP"
                    )
            else:
                st.caption("Sin consumo registrado.")

        with st.expander("📜 Ultimas operaciones"):
            _recent = _tracker.get_usage_history(_get_user_id(), limit=10)
            if _recent:
                for _r in _recent:
                    _date_label = _r.created_at[:16] if _r.created_at else "N/A"
                    st.caption(
                        f"`{_r.operation}` — in:{_r.input_tokens} out:{_r.output_tokens} "
                        f"${_r.total_cost_cop:,.4f} COP ({_date_label})"
                    )
            else:
                st.caption("Sin historial.")

        st.divider()
    except Exception as _tk_err:
        logger.debug(f"Token tracker sidebar no disponible: {_tk_err}")

    st.header("Navegación Rápida")
    if st.button("🤖 Asistente de Entrevista", type="primary", use_container_width=True):
        st.session_state.current_step = 4
        st.rerun()
    if st.button("📝 Inicio / Cargar CV", use_container_width=True):
        st.session_state.current_step = 0
        st.rerun()

    st.divider()

    st.header("📚 Historial de CVs")

    # Inicializar DB
    db = CVDatabase()
    try:
        history = db.get_all_cvs(user_id=_get_user_id())
    except Exception as e:
        st.error(f"Error leyendo historial: {e}")
        history = []

    if not history:
        st.info("No hay CVs generados aún.")
    else:
        st.metric("CVs Generados", len(history))

        if st.button("🗑️ Limpiar Historial", type="secondary", use_container_width=True):
            db.clear_all(user_id=_get_user_id())
            st.rerun()

        st.divider()

        # Mostrar lista inversa (más recientes arriba) - get_all_cvs ya los trae ordenados
        for cv_item in history:
            # Formatear fecha
            date_str = cv_item["created_at"]
            try:
                # Intentar parsear fecha para mostrarla más bonita
                # Formato DB: YYYY-MM-DD HH:MM:SS
                date_obj = date_str.split(" ")[0]
                time_obj = date_str.split(" ")[1][:5]
                display_date = f"{date_obj} {time_obj}"
            except:
                display_date = date_str

            with st.expander(f"📄 {cv_item['job_title']} ({display_date})"):
                st.caption(f"**Empresa:** {cv_item.get('company', 'N/A')}")
                st.caption(f"**Idioma:** {cv_item.get('language', 'N/A')}")
                st.caption(f"**Tema:** {cv_item.get('theme', 'N/A')}")

                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button(
                        "📂 Cargar", key=f"load_{cv_item['id']}", use_container_width=True
                    ):
                        # Cargar datos completos
                        full_cv = db.get_cv_by_id(cv_item["id"], user_id=_get_user_id())
                        if full_cv:
                            # Restaurar estado
                            st.session_state.yaml_generated = full_cv["yaml_content"]
                            st.session_state.pdf_path = full_cv["pdf_path"]
                            st.session_state.questions_completed = True
                            st.session_state.cv_text = (
                                full_cv.get("original_cv") or st.session_state.cv_text
                            )
                            st.session_state.job_description = (
                                full_cv.get("job_description") or st.session_state.job_description
                            )

                            st.toast(f"✅ CV cargado: {cv_item['job_title']}")
                            # Navegar automáticamente al resultado
                            st.session_state.current_step = 3
                            st.rerun()

                with col_b:
                    if st.button(
                        "❌ Borrar",
                        key=f"del_{cv_item['id']}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        db.delete_cv(cv_item["id"])
                        st.rerun()

    st.divider()

    # NUEVA SECCIÓN: Memoria de Habilidades
    with st.expander("🧠 Memoria de Habilidades"):
        st.info("Aquí puedes ver y editar lo que la IA ha aprendido de ti.")

        # Cargar skills guardadas
        try:
            saved_skills = db.get_all_skill_answers()  # Retorna dict {skill: answer}
        except Exception as e:
            st.error(f"Error cargando skills: {e}")
            saved_skills = {}

        if not saved_skills:
            st.caption("No hay habilidades guardadas aún.")
        else:
            # Selector de skill
            skill_list = list(saved_skills.keys())
            selected_skill = st.selectbox("Selecciona una habilidad:", skill_list)

            if selected_skill:
                current_answer = saved_skills[selected_skill]

                # Editor
                new_answer = st.text_area(
                    f"Tu experiencia con {selected_skill}:",
                    value=current_answer,
                    height=150,
                    key=f"edit_skill_{selected_skill}",
                )

                col_save, col_del = st.columns(2)

                with col_save:
                    if st.button(
                        "💾 Guardar", key=f"save_skill_{selected_skill}", use_container_width=True
                    ):
                        db.save_skill_answer(selected_skill, new_answer)
                        st.success("✅ Actualizado!")
                        time.sleep(0.5)
                        st.rerun()

                with col_del:
                    if st.button(
                        "🗑️ Borrar",
                        key=f"del_skill_{selected_skill}",
                        type="secondary",
                        use_container_width=True,
                    ):
                        db.delete_skill_answer(selected_skill)
                        st.warning(f"❌ {selected_skill} eliminado de memoria.")
                        time.sleep(0.5)
                        st.rerun()

    st.divider()

    st.header("ℹ️ Información")
    st.markdown("""
    **Cómo funciona:**
    1. **Inputs**: Proporciona tu CV actual y la descripción de la vacante
    2. **Análisis**: La IA identifica brechas entre tu CV y la vacante
    3. **Preguntas**: Responde preguntas para completar información faltante
    4. **Resultado**: Obtén tu CV optimizado en YAML y PDF
    """)

    st.divider()

    if st.button("🔄 Reiniciar Proceso", type="secondary", use_container_width=True):
        # Resetear todo el estado
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# RENDERIZAR CONTENIDO SEGÚN EL PASO ACTUAL
# ==========================================

# TAB 1: INPUTS
if st.session_state.current_step == 0:
    st.header("📝 Proporciona tu información")

    st.info(
        "💡 **Tip:** Cuanto más detallado sea tu CV, mejor será el análisis y las recomendaciones."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Tu CV Actual")
        cv_input_method = st.radio(
            "¿Cómo quieres proporcionar tu CV?", ["Pegar texto", "Subir PDF"], horizontal=True
        )

        if cv_input_method == "Pegar texto":
            st.session_state.cv_text = st.text_area(
                "Pega aquí el contenido de tu CV actual",
                value=st.session_state.cv_text,
                height=300,
                placeholder="Ejemplo:\n\nJuan Pérez\nSoftware Engineer\njuan@example.com\n\nExperiencia:\n- Company XYZ (2020-2023)\n  Desarrollé aplicaciones web...\n\nEducación:\n- Universidad ABC\n  Ingeniería en Sistemas\n\nHabilidades:\nPython, JavaScript, SQL...",
            )

            if st.session_state.cv_text:
                word_count = len(st.session_state.cv_text.split())
                st.caption(f"📊 {word_count} palabras | {len(st.session_state.cv_text)} caracteres")

            # Botón para guardar como CV Base
            if st.button(
                "💾 Guardar como mi CV Base",
                help="Guarda este texto como tu CV predeterminado para futuras sesiones",
            ):
                if len(st.session_state.cv_text.strip()) > 50:
                    try:
                        db = CVDatabase()
                        db.save_base_cv(st.session_state.cv_text, user_id=_get_user_id())
                        st.success("✅ CV Base actualizado correctamente")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error guardando CV base: {e}")
                else:
                    st.warning("⚠️ El texto es muy corto para guardarlo como base")
        else:
            uploaded_file = st.file_uploader(
                "Sube tu CV en PDF",
                type=["pdf"],
                help="El PDF debe tener texto seleccionable (no escaneos)",
            )

            if uploaded_file:
                # Detectar cambio de archivo
                file_hash = hash(uploaded_file.getvalue())

                # Si es un archivo nuevo o no hay texto extraído, extraer automáticamente
                if (
                    st.session_state.last_uploaded_file_hash != file_hash
                    or not st.session_state.cv_text
                ):
                    with st.spinner("📄 Extrayendo texto del PDF automáticamente..."):
                        try:
                            # Guardar archivo temporalmente
                            with tempfile.NamedTemporaryFile(
                                delete=False, suffix=".pdf"
                            ) as tmp_file:
                                tmp_file.write(uploaded_file.getvalue())
                                tmp_path = tmp_file.name

                            # Usar CVParser para extraer texto
                            parser = CVParser()
                            cv_data = parser.parse_pdf(tmp_path)

                            # Guardar el texto extraído
                            st.session_state.cv_text = cv_data.raw_text
                            st.session_state.last_uploaded_file_hash = file_hash

                            # Limpiar archivo temporal
                            Path(tmp_path).unlink()

                            st.success("✅ Texto extraído correctamente!")
                            st.rerun()

                        except Exception as e:
                            st.error(f"❌ Error al extraer texto del PDF: {str(e)}")
                            st.info("💡 Intenta copiar y pegar el texto manualmente")

                # Mostrar preview del texto extraído
                if st.session_state.cv_text:
                    with st.expander("👁️ Ver texto extraído", expanded=False):
                        st.text_area(
                            "Texto extraído del PDF:",
                            value=st.session_state.cv_text,
                            height=200,
                            disabled=True,
                        )

                    # Botón para guardar como CV Base (versión PDF)
                    if st.button(
                        "💾 Guardar como mi CV Base",
                        key="save_base_cv_pdf",
                        help="Guarda este texto como tu CV predeterminado para futuras sesiones",
                    ):
                        if len(st.session_state.cv_text.strip()) > 50:
                            try:
                                db = CVDatabase()
                                db.save_base_cv(st.session_state.cv_text, user_id=_get_user_id())
                                st.success("✅ CV Base actualizado correctamente")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error guardando CV base: {e}")

    with col2:
        st.subheader("Descripción de la Vacante")
        st.session_state.job_description = st.text_area(
            "Pega aquí la descripción completa de la vacante",
            value=st.session_state.job_description,
            height=300,
            placeholder="Ejemplo:\n\nSenior Python Developer\n\nRequisitos:\n- 5+ años de experiencia con Python\n- Django, Flask\n- PostgreSQL, MongoDB\n- Docker, Kubernetes\n- Liderazgo de equipos\n\nResponsabilidades:\n- Diseñar arquitecturas escalables\n- Mentoría a desarrolladores junior\n- Code reviews...",
        )

        if st.session_state.job_description:
            word_count = len(st.session_state.job_description.split())
            st.caption(
                f"📊 {word_count} palabras | {len(st.session_state.job_description)} caracteres"
            )

    st.divider()

    # Configuración adicional
    st.subheader("⚙️ Configuración del CV")

    col3, col4 = st.columns(2)

    with col3:
        # Mapeo de idiomas a códigos
        language_map = {"Español": "es", "English": "en", "Português": "pt", "Français": "fr"}

        selected_lang_display = st.selectbox(
            "🌐 Idioma del CV a generar",
            ["Español", "English", "Português", "Français"],
            index=["Español", "English", "Português", "Français"].index(
                st.session_state.selected_language
            ),
            help="El CV final se generará en este idioma",
        )
        st.session_state.selected_language = selected_lang_display

    with col4:
        # Descripciones de temas
        theme_descriptions = {
            "classic": "📘 Classic - Diseño limpio y profesional, ideal para la mayoría de industrias",
            "sb2nov": "💼 Sb2nov - Diseño moderno de dos columnas, perfecto para tech/startups",
            "moderncv": "🎨 ModernCV - Estilo elegante con sidebar, ideal para creativos",
            "engineeringresumes": "⚙️ Engineering - Diseño técnico optimizado para ingenieros",
        }

        selected_theme = st.selectbox(
            "🎨 Tema de RenderCV",
            ["classic", "sb2nov", "moderncv", "engineeringresumes"],
            index=["classic", "sb2nov", "moderncv", "engineeringresumes"].index(
                st.session_state.selected_theme
            ),
            format_func=lambda x: theme_descriptions[x],
            help="El tema define el estilo visual de tu CV",
        )
        st.session_state.selected_theme = selected_theme

    st.divider()

    # Validación y AUTO-AVANCE
    validation_errors = []

    if not st.session_state.cv_text or len(st.session_state.cv_text.strip()) < 50:
        validation_errors.append("📄 CV actual (min 50 caracteres)")
    if not st.session_state.job_description or len(st.session_state.job_description.strip()) < 30:
        validation_errors.append("📋 Descripción de vacante (min 30 caracteres)")

    if validation_errors:
        st.warning(f"⚠️ **Para continuar, completa:** {', '.join(validation_errors)}")
        st.button("🚀 Comenzar Análisis (Deshabilitado)", disabled=True)
    else:
        st.success("✅ Inputs válidos. Configura tu idioma y tema, luego inicia el análisis.")

        # Botón manual para avanzar
        if st.button("🚀 Comenzar Análisis", type="primary", use_container_width=True):
            st.session_state.current_step = 1
            st.rerun()

# TAB 2: ANÁLISIS
elif st.session_state.current_step == 1:
    st.header("🔍 Análisis de Brechas (Gap Analysis)")

    # Auto-ejecución del análisis
    if not st.session_state.gap_analysis_done:
        # Verificar que existe API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            st.error("❌ **Error:** No se encontró GOOGLE_API_KEY en el archivo .env")
            st.info("💡 Agrega tu API key de Gemini en el archivo `.env`")
            st.stop()

        # Verificar limite de tokens antes de ejecutar IA
        if _is_user_blocked():
            st.error("🚫 Has alcanzado tu limite de uso de IA. Contacta al administrador.")
            st.stop()

        with st.spinner("🤖 Analizando tu CV vs. la vacante con Gemini AI..."):
            try:
                # Crear cliente de Gemini
                gemini_client = GeminiClient()

                # Inicializar GapAnalyzer con el cliente
                gap_analyzer = GapAnalyzer(gemini_client=gemini_client)

                # Ejecutar Gap Analysis
                gap_result = gap_analyzer.analyze(
                    cv_text=st.session_state.cv_text,
                    job_description=st.session_state.job_description,
                )

                # Registrar tokens consumidos
                _record_token_usage(gemini_client, "gap_analysis")

                # Extraer datos para la UI
                must_haves_list = [s.name for s in gap_result.job_requirements.get_must_haves()]
                found_skills_list = [s.name for s in gap_result.skills_found]
                all_gaps_list = [g.skill_name for g in gap_result.get_all_gaps()]
                recommendations = gap_analyzer.get_recommendations(gap_result)

                # Guardar resultados en session_state
                st.session_state.gap_analysis_result = {
                    "job_requirements": gap_result.job_requirements,
                    "gap_analysis": gap_result,
                    "must_haves": must_haves_list,
                    "found_in_cv": found_skills_list,
                    "gaps": all_gaps_list,
                    "recommendations": recommendations,
                }
                st.session_state.gap_analysis_done = True

                st.success("✅ ¡Análisis completado!")
                time.sleep(1)  # Pequeña pausa para ver el mensaje
                st.rerun()

            except Exception as e:
                st.error(f"❌ **Error al ejecutar el análisis:** {str(e)}")
                st.exception(e)
                if st.button("🔄 Reintentar"):
                    st.rerun()

    else:
        # Mostrar resultados del análisis
        result = st.session_state.gap_analysis_result
        gap_analysis = result.get("gap_analysis")

        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Requisitos Totales",
                len(result.get("must_haves", [])),
                help="Total de habilidades must-have identificadas",
            )

        with col2:
            matched_count = len(result.get("found_in_cv", []))
            st.metric(
                "Encontradas en CV",
                matched_count,
                delta=f"+{matched_count}",
                delta_color="normal",
                help="Habilidades que ya tienes en tu CV",
            )

        with col3:
            gap_count = len(result.get("gaps", []))
            st.metric(
                "Brechas Detectadas",
                gap_count,
                delta=f"-{gap_count}",
                delta_color="inverse",
                help="Habilidades que faltan en tu CV",
            )

        with col4:
            if len(result.get("must_haves", [])) > 0:
                match_percentage = int((matched_count / len(result.get("must_haves", []))) * 100)
            else:
                match_percentage = 0

            st.metric(
                "Compatibilidad",
                f"{match_percentage}%",
                help="Porcentaje de requisitos que cumples",
            )

        st.divider()

        # Requisitos de la vacante
        st.subheader("📋 Requisitos Must-Have de la Vacante")

        if result.get("must_haves"):
            # Agrupar en filas de 4
            must_haves = result.get("must_haves", [])
            rows = [must_haves[i : i + 4] for i in range(0, len(must_haves), 4)]

            for row in rows:
                cols = st.columns(4)
                for idx, skill in enumerate(row):
                    with cols[idx]:
                        # Verificar si está en found_in_cv
                        if skill in result.get("found_in_cv", []):
                            st.success(f"✅ {skill}")
                        else:
                            st.error(f"❌ {skill}")
        else:
            st.info("No se identificaron requisitos must-have específicos")

        st.divider()

        # Habilidades encontradas
        st.subheader("✅ Habilidades Encontradas en tu CV")

        if result.get("found_in_cv"):
            found_skills = result.get("found_in_cv", [])

            # Mostrar en badges verdes
            cols = st.columns(5)
            for idx, skill in enumerate(found_skills):
                with cols[idx % 5]:
                    st.markdown(f":green[✓ **{skill}**]")

            st.success(f"🎉 Tienes {len(found_skills)} de las habilidades requeridas!")
        else:
            st.warning("⚠️ No se encontraron coincidencias directas con los requisitos")
            st.info(
                "💡 Esto puede significar que necesitas reescribir tu CV para resaltar mejor tus habilidades"
            )

        st.divider()

        # Brechas identificadas
        st.subheader("⚠️ Brechas Identificadas (Skills Faltantes)")

        if result.get("gaps"):
            gaps = result.get("gaps", [])

            st.warning(f"Se identificaron **{len(gaps)} brechas** entre tu CV y la vacante")

            # Mostrar gaps en columnas
            cols = st.columns(3)
            for idx, gap in enumerate(gaps):
                with cols[idx % 3]:
                    st.markdown(f"🔴 **{gap}**")

            st.info("""
            💡 **Siguiente paso:** En el tab de Preguntas, la IA te consultará sobre estas habilidades.
            Si tienes experiencia con ellas (pero no las mencionaste en tu CV), podrás agregarlas!
            """)
        else:
            st.success("🎉 ¡Excelente! No se identificaron brechas significativas")
            st.balloons()
            st.info("Tu CV parece estar muy alineado con los requisitos de la vacante")

        st.divider()

        # Recomendaciones de la IA
        recommendations = result.get("recommendations", {})

        if recommendations:
            st.subheader("💡 Recomendaciones de la IA")

            # Mostrar recomendaciones críticas
            if recommendations.get("critical"):
                for rec in recommendations["critical"]:
                    st.error(f"🚨 {rec}")

            # Mostrar recomendaciones importantes
            if recommendations.get("important"):
                for rec in recommendations["important"]:
                    st.warning(f"⚠️ {rec}")

            # Mostrar sugerencias
            if recommendations.get("nice_to_have"):
                with st.expander("ℹ️ Ver sugerencias adicionales"):
                    for rec in recommendations["nice_to_have"]:
                        st.info(rec)

        # AVANCE MANUAL
        st.divider()

        col_nav_1, col_nav_2 = st.columns([1, 3])

        with col_nav_1:
            # Botón para re-analizar (manual override)
            if st.button("🔄 Re-analizar", type="secondary", use_container_width=True):
                st.session_state.gap_analysis_done = False
                st.rerun()

        with col_nav_2:
            st.success("✅ Análisis completado. Revisa los resultados arriba.")
            if st.button("💬 Continuar a la Entrevista", type="primary", use_container_width=True):
                st.session_state.current_step = 2
                st.rerun()

# TAB 3: PREGUNTAS
elif st.session_state.current_step == 2:
    st.header("💬 Conversación con el Estratega de Carrera")

    if not st.session_state.gap_analysis_done:
        st.warning("⚠️ Primero completa el análisis de brechas")
        st.session_state.current_step = 1
        st.rerun()
    else:
        # Generar preguntas si es la primera vez y no hay historial
        if not st.session_state.generated_questions and not st.session_state.questions_completed:
            # Verificar limite de tokens
            if _is_user_blocked():
                st.error("🚫 Has alcanzado tu limite de uso de IA. Contacta al administrador.")
                st.stop()

            with st.spinner("🤖 Generando preguntas estratégicas..."):
                try:
                    # Configurar idioma
                    lang_map = {
                        "Español": Language.SPANISH,
                        "English": Language.ENGLISH,
                        "Português": Language.PORTUGUESE,
                        "Français": Language.FRENCH,
                    }
                    # Usar get con default
                    selected_lang = st.session_state.selected_language
                    # Extraer el string si es un objeto selectbox (a veces pasa en streamlit)
                    if not isinstance(selected_lang, str):
                        selected_lang = "Español"

                    lang_enum = lang_map.get(selected_lang, Language.SPANISH)

                    # Inicializar generador
                    gemini_client = GeminiClient()
                    question_gen = QuestionGenerator(ai_client=gemini_client, language=lang_enum)

                    # Generar preguntas
                    gap_result = st.session_state.gap_analysis_result["gap_analysis"]
                    questions = question_gen.generate_questions(
                        gap_result, max_questions=5, prioritize_critical=True
                    )

                    # Registrar tokens consumidos
                    _record_token_usage(gemini_client, "question_generation")

                    st.session_state.generated_questions = questions

                    # NUEVO: Verificar memoria de habilidades
                    db = CVDatabase()
                    prefilled = {}
                    for q in questions:
                        skill_name = q.gap.skill_name
                        stored_answer = db.get_skill_answer(skill_name)
                        if stored_answer:
                            prefilled[skill_name] = stored_answer

                    st.session_state.prefilled_answers = prefilled

                    # Iniciar conversación
                    if questions:
                        first_q = questions[0]
                        st.session_state.conversation_history = [
                            {"role": "ai", "text": first_q.text, "question_idx": 0}
                        ]
                    else:
                        st.session_state.conversation_history = [
                            {
                                "role": "ai",
                                "text": "¡Tu CV está muy completo! No tengo preguntas adicionales. Puedes proceder a generar tu CV.",
                            }
                        ]
                        st.session_state.questions_completed = True
                        st.rerun()

                except Exception as e:
                    st.error(f"Error generando preguntas: {e}")
                    # Fallback manual
                    st.session_state.questions_completed = True

        # Mostrar instrucciones
        if not st.session_state.questions_completed:
            st.info("""
            📌 **Instrucciones:**
            Responde brevemente a las preguntas. La IA usará tus respuestas para mejorar tu CV.
            Si no tienes experiencia en algo, sé honesto y dilo (o salta la pregunta).
            """)

        st.divider()

        # Historial de chat
        for msg in st.session_state.conversation_history:
            if msg["role"] == "ai":
                with st.chat_message("assistant"):
                    st.markdown(msg["text"])
            else:
                with st.chat_message("user"):
                    st.markdown(msg["text"])

        # Input area
        if not st.session_state.questions_completed and st.session_state.generated_questions:
            idx = st.session_state.current_question_index

            if idx < len(st.session_state.generated_questions):
                current_q = st.session_state.generated_questions[idx]

                # Usar form para enviar con Enter
                with st.form(key=f"question_form_{idx}"):
                    # Verificar si hay respuesta pre-cargada
                    skill_name_current = current_q.gap.skill_name
                    default_answer = st.session_state.prefilled_answers.get(skill_name_current, "")

                    label_text = "Tu respuesta:"
                    if default_answer:
                        label_text = "💡 Respuesta recuperada de tu historial (puedes editarla):"

                    user_response = st.text_area(
                        label_text,
                        value=default_answer,
                        height=100,
                        placeholder="Ej: Sí, he usado esta tecnología en el proyecto X para...",
                    )

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        submit = st.form_submit_button(
                            "📤 Enviar Respuesta", type="primary", use_container_width=True
                        )
                    with col2:
                        skip = st.form_submit_button(
                            "⏭️ Saltar / No tengo experiencia",
                            type="secondary",
                            use_container_width=True,
                        )

                    if submit or skip:
                        # Guardar respuesta
                        answer_text = (
                            user_response
                            if submit and user_response
                            else "No tengo experiencia en esto."
                        )

                        # Guardar en diccionario de respuestas
                        skill_name = current_q.gap.skill_name
                        st.session_state.user_answers[skill_name] = answer_text

                        # NUEVO: Guardar en memoria persistente si es una respuesta válida (no skip vacío o negativa default)
                        # Nota: Si el usuario confirma "No tengo experiencia", también podríamos querer guardarlo para no preguntar de nuevo?
                        # Por ahora guardamos todo lo que el usuario envía explícitamente.
                        if submit and user_response:
                            db = CVDatabase()
                            db.save_skill_answer(skill_name, answer_text)

                        # Agregar a historial
                        st.session_state.conversation_history.append(
                            {"role": "user", "text": answer_text}
                        )

                        # Avanzar
                        next_idx = idx + 1
                        st.session_state.current_question_index = next_idx

                        if next_idx < len(st.session_state.generated_questions):
                            next_q = st.session_state.generated_questions[next_idx]
                            st.session_state.conversation_history.append(
                                {"role": "ai", "text": next_q.text, "question_idx": next_idx}
                            )
                        else:
                            st.session_state.questions_completed = True
                            st.session_state.conversation_history.append(
                                {
                                    "role": "ai",
                                    "text": "✅ ¡Gracias! He recopilado toda la información necesaria. Generando tu CV automáticamente...",
                                }
                            )

                        st.rerun()

        # AUTO-AVANCE: Si preguntas completadas, ir al siguiente paso
        if st.session_state.questions_completed:
            st.success("🎉 ¡Entrevista completada! Generando tu CV...")

            # Mostrar resumen de respuestas
            if st.session_state.user_answers:
                with st.expander("📄 Ver tus respuestas recopiladas"):
                    for skill, answer in st.session_state.user_answers.items():
                        st.markdown(f"**{skill}:** {answer}")

            # Auto-avance
            with st.spinner("Preparando resultado final..."):
                time.sleep(2)
                st.session_state.current_step = 3
                st.rerun()

# TAB 4: RESULTADO
elif st.session_state.current_step == 3:
    st.header("✅ Tu CV Optimizado")

    if not st.session_state.questions_completed:
        st.warning("⚠️ Primero completa la conversación")
        st.session_state.current_step = 2
        st.rerun()
    else:
        # Botón para refinar respuestas (Feature US-022)
        with st.expander("🛠️ Opciones de Edición", expanded=True):
            st.info(
                "¿Algo no quedó bien? Puedes volver a las preguntas para ajustar tus respuestas."
            )
            if st.button(
                "✏️ Actualizar preguntas / Refinar respuestas",
                type="secondary",
                use_container_width=True,
            ):
                # Resetear estado para permitir edición
                st.session_state.questions_completed = False
                st.session_state.current_step = 2
                st.session_state.current_question_index = 0
                # NOTA: No borramos user_answers para que sirvan de pre-llenado
                st.session_state.yaml_generated = None  # Forzar regeneración
                st.rerun()

        if not st.session_state.yaml_generated:
            # Verificar limite de tokens
            if _is_user_blocked():
                st.error("🚫 Has alcanzado tu limite de uso de IA. Contacta al administrador.")
                st.stop()

            # AUTO-GENERACIÓN
            try:
                logger.info("Iniciando generación automática de CV (Tab 4)")

                # Inicializar clientes
                gemini_client = GeminiClient()

                # Mapeo de idioma (definir temprano para usar en todos los prompts)
                lang_code = {
                    "Español": "es",
                    "English": "en",
                    "Português": "pt",
                    "Français": "fr",
                }.get(st.session_state.selected_language, "es")

                language_name = "English" if lang_code == "en" else "Español"

                # 1. Estructurar Datos del CV (Contacto, Educación, Experiencia, Skills)
                with st.spinner("🧠 Estructurando información del CV..."):
                    logger.info("Estructurando información del CV...")
                    prompt = PromptManager.get_data_structuring_prompt(
                        st.session_state.cv_text, language=language_name
                    )

                    response = gemini_client.generate(prompt)
                    import json

                    # Limpiar JSON
                    json_str = response.text.strip()
                    if "```json" in json_str:
                        json_str = json_str.split("```json")[1].split("```")[0].strip()
                    elif "```" in json_str:
                        json_str = json_str.split("```")[1].split("```")[0].strip()

                    structured_data = json.loads(json_str)
                    logger.info(
                        f"Datos estructurados: {len(structured_data.get('experience', []))} experiencias encontradas"
                    )

                # 2. Clasificar y Procesar Respuestas del Usuario (OPTIMIZADO CON BATCHING Y PARALELISMO)
                gap_result = st.session_state.gap_analysis_result["gap_analysis"]
                user_answers = st.session_state.user_answers

                # Inicializar listas para clasificaciones
                experience_enrichments = []  # Para enriquecer experiencia laboral existente
                projects_to_create = []  # Para crear sección de proyectos

                if user_answers:
                    with st.spinner("🔍 Clasificando tus respuestas (Optimizado)..."):
                        logger.info("Clasificando respuestas del usuario en batch...")

                        # Obtener nombres de empresas conocidas del CV
                        known_companies = [
                            exp.get("company", "") for exp in structured_data.get("experience", [])
                        ]

                        # Preparar lista de respuestas válidas para el prompt
                        answers_list = []
                        for skill, answer in user_answers.items():
                            if "no tengo experiencia" not in answer.lower():
                                answers_list.append({"skill": skill, "answer": answer})

                        if answers_list:
                            try:
                                # Llamada BATCH única a la IA
                                classifier_prompt = (
                                    PromptManager.get_batch_user_response_classifier_prompt(
                                        user_answers_list=answers_list,
                                        known_companies=known_companies,
                                    )
                                )

                                classifier_response = gemini_client.generate(classifier_prompt)
                                classifier_text = classifier_response.text.strip()

                                # Limpiar JSON
                                if "```json" in classifier_text:
                                    classifier_text = (
                                        classifier_text.split("```json")[1].split("```")[0].strip()
                                    )
                                elif "```" in classifier_text:
                                    classifier_text = (
                                        classifier_text.split("```")[1].split("```")[0].strip()
                                    )

                                classifications = json.loads(classifier_text)

                                # Procesar clasificaciones
                                for classification in classifications:
                                    skill_name = classification.get("skill")

                                    if classification["classification"] == "EXPERIENCIA_LABORAL":
                                        experience_enrichments.append(
                                            {
                                                "skill": skill_name,
                                                "company": classification.get("company_name"),
                                                "description": classification.get("description"),
                                            }
                                        )
                                        logger.info(
                                            f"{skill_name} clasificado como EXPERIENCIA_LABORAL en {classification.get('company_name')}"
                                        )

                                    elif classification["classification"] in [
                                        "PROYECTO_ACADEMICO",
                                        "PROYECTO_PERSONAL",
                                    ]:
                                        projects_to_create.append(
                                            {
                                                "skill": skill_name,
                                                "project_name": classification.get("project_name"),
                                                "project_type": classification["classification"],
                                                "description": classification.get("description"),
                                            }
                                        )
                                        logger.info(
                                            f"{skill_name} clasificado como {classification['classification']}: {classification.get('project_name')}"
                                        )

                            except Exception as e:
                                logger.error(f"Error en clasificación batch: {e}")
                                # Fallback (podría implementarse lógica individual aquí si falla el batch)

                # EJECUCIÓN PARALELA DE GENERACIÓN DE CONTENIDO
                with st.spinner("🚀 Generando contenido enriquecido en paralelo..."):
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        futures = {}

                        # 1. Tareas de Enriquecimiento de Experiencia
                        enrichment_tasks = []
                        if experience_enrichments and structured_data.get("experience"):
                            # Agrupar enriquecimientos por empresa
                            enrichments_by_company = {}
                            for enrichment in experience_enrichments:
                                company = enrichment["company"]
                                if company not in enrichments_by_company:
                                    enrichments_by_company[company] = []
                                enrichments_by_company[company].append(enrichment)

                            # Obtener keywords de la vacante
                            job_keywords = [
                                s.name for s in gap_result.job_requirements.get_must_haves()
                            ]

                            for i, exp in enumerate(structured_data["experience"]):
                                company_name = exp.get("company", "")
                                if company_name in enrichments_by_company:
                                    # Preparar prompt
                                    current_highlights = "\n".join(
                                        [f"- {h}" for h in exp.get("highlights", [])]
                                    )
                                    skills_to_add = "\n".join(
                                        [
                                            f"- {e['skill']}: {e['description']}"
                                            for e in enrichments_by_company[company_name]
                                        ]
                                    )

                                    prompt = PromptManager.get_experience_enrichment_prompt(
                                        position=exp.get("position", ""),
                                        company=company_name,
                                        duration=f"{exp.get('start_date', '')} - {exp.get('end_date', '')}",
                                        current_highlights=current_highlights,
                                        user_confirmed_skills=skills_to_add,
                                        job_keywords=job_keywords,
                                        language=language_name,
                                    )

                                    # Submit task
                                    future = executor.submit(gemini_client.generate, prompt)
                                    futures[future] = {
                                        "type": "enrichment",
                                        "index": i,
                                        "company": company_name,
                                    }

                        # 2. Tareas de Creación de Proyectos
                        if projects_to_create:
                            for i, project_data in enumerate(projects_to_create):
                                prompt = PromptManager.get_project_entry_generation_prompt(
                                    project_name=project_data["project_name"],
                                    project_type="académico"
                                    if "ACADEMICO" in project_data["project_type"]
                                    else "personal",
                                    main_skill=project_data["skill"],
                                    user_description=project_data["description"],
                                    language=language_name,
                                )
                                future = executor.submit(gemini_client.generate, prompt)
                                futures[future] = {"type": "project", "data": project_data}

                        # 3. Tarea de Resumen Profesional
                        # Preparar datos
                        education_summary = ", ".join(
                            [
                                f"{e.get('degree', 'N/A')} en {e.get('institution', 'N/A')}"
                                for e in structured_data.get("education", [])
                            ]
                        )
                        experience_summary = ", ".join(
                            [
                                f"{e.get('position', 'N/A')} en {e.get('company', 'N/A')}"
                                for e in structured_data.get("experience", [])
                            ]
                        )
                        skills_summary = ", ".join(
                            [s.get("details", "") for s in structured_data.get("skills", [])]
                        )

                        years_exp = "2-3 años"
                        if structured_data.get("experience"):
                            try:
                                first_exp = structured_data["experience"][0]
                                start = first_exp.get("start_date", "2020")
                                if start and len(start) >= 4:
                                    years_exp = f"{2026 - int(start[:4])} años"
                            except:
                                pass

                        must_haves = "\n".join(
                            [
                                f"- {s}"
                                for s in st.session_state.gap_analysis_result.get("must_haves", [])
                            ]
                        )

                        summary_prompt = PromptManager.get_summary_generation_prompt(
                            job_description=st.session_state.job_description,
                            education_summary=education_summary,
                            experience_summary=experience_summary,
                            skills_summary=skills_summary,
                            years_experience=years_exp,
                            must_have_skills=must_haves,
                            language=language_name,
                        )
                        future_summary = executor.submit(gemini_client.generate, summary_prompt)
                        futures[future_summary] = {"type": "summary"}

                        # 4. Tarea de Priorización de Skills
                        current_skills_text = json.dumps(
                            structured_data.get("skills", []), ensure_ascii=False, indent=2
                        )
                        must_haves_list = st.session_state.gap_analysis_result.get("must_haves", [])
                        must_haves_text = ", ".join(must_haves_list)
                        job_title = "Desarrollador"  # TODO: Improve extraction

                        skill_prompt = PromptManager.get_skill_prioritization_prompt(
                            current_skills=current_skills_text,
                            must_have_skills=must_haves_text,
                            job_title=job_title,
                        )
                        future_skills = executor.submit(gemini_client.generate, skill_prompt)
                        futures[future_skills] = {"type": "skills"}

                        # PROCESAR RESULTADOS A MEDIDA QUE LLEGAN
                        new_projects = []

                        for future in concurrent.futures.as_completed(futures):
                            task_info = futures[future]
                            try:
                                response = future.result()
                                text = response.text.strip()

                                # Limpiar marcadores JSON si existen
                                if "```json" in text:
                                    text = text.split("```json")[1].split("```")[0].strip()
                                elif "```" in text:
                                    text = text.split("```")[1].split("```")[0].strip()

                                if task_info["type"] == "enrichment":
                                    # Procesar texto enriquecido (bullet points)
                                    enriched_highlights = [
                                        line.strip().lstrip("-").lstrip("•").lstrip("*").strip()
                                        for line in text.split("\n")
                                        if line.strip() and not line.strip().startswith("#")
                                    ]
                                    structured_data["experience"][task_info["index"]][
                                        "highlights"
                                    ] = enriched_highlights
                                    logger.info(
                                        f"Experiencia enriquecida (Async): {task_info['company']}"
                                    )

                                elif task_info["type"] == "project":
                                    project_entry = json.loads(text)
                                    new_projects.append(
                                        {
                                            "name": task_info["data"]["project_name"],
                                            "summary": project_entry.get("summary"),
                                            "start_date": None,
                                            "end_date": None,
                                            "highlights": project_entry.get("highlights", []),
                                        }
                                    )
                                    logger.info(
                                        f"Proyecto creado (Async): {task_info['data']['project_name']}"
                                    )

                                elif task_info["type"] == "summary":
                                    if text.startswith('"') and text.endswith('"'):
                                        text = text[1:-1]
                                    structured_data["summary"] = text
                                    logger.info("Resumen generado (Async)")

                                elif task_info["type"] == "skills":
                                    prioritized_skills = json.loads(text)
                                    structured_data["skills"] = prioritized_skills
                                    logger.info("Skills priorizadas (Async)")

                            except Exception as e:
                                logger.error(f"Error en tarea {task_info['type']}: {e}")

                        # Agregar proyectos generados
                        if new_projects:
                            structured_data["projects"] = new_projects

                # Registrar tokens consumidos (todas las llamadas IA acumuladas)
                _record_token_usage(gemini_client, "cv_generation")

                # 3. Generar YAML
                with st.spinner("📄 Generando archivo YAML..."):
                    logger.info("Generando YAML...")
                    yaml_gen = YAMLGenerator()

                    yaml_content = yaml_gen.parse_and_generate(
                        structured_data=structured_data,
                        theme=st.session_state.selected_theme,
                        language=lang_code,
                    )
                    st.session_state.yaml_generated = yaml_content

                # 4. Renderizar PDF
                with st.spinner("🎨 Renderizando PDF con RenderCV..."):
                    logger.info("Renderizando PDF...")
                    pdf_renderer = PDFRenderer(output_dir="outputs")
                    pdf_path = pdf_renderer.render_from_string(yaml_content)
                    st.session_state.pdf_path = pdf_path

                # 5. Guardar en Historial
                with st.spinner("💾 Guardando en historial..."):
                    logger.info("Guardando en historial...")
                    db = CVDatabase()
                    db.save_cv(
                        job_title="CV Generado",  # TODO: Extraer título real
                        yaml_content=yaml_content,
                        company="N/A",
                        language=lang_code,
                        theme=st.session_state.selected_theme,
                        pdf_path=pdf_path,
                        original_cv=st.session_state.cv_text,
                        job_description=st.session_state.job_description,
                    )

                logger.info("CV generado exitosamente")
                st.success("✅ ¡CV Generado exitosamente!")
                st.balloons()
                st.rerun()

            except Exception as e:
                logger.error(f"Error durante la generación de CV: {e}", exc_info=True)
                st.error(f"❌ Error durante la generación: {str(e)}")
                st.info("Intenta nuevamente. Si el error persiste, verifica tus inputs.")
                with st.expander("Ver detalles del error"):
                    st.exception(e)
                if st.button("🔄 Reintentar"):
                    st.rerun()

        else:
            # Mostrar resultados
            st.subheader("🎉 ¡Tu CV está listo!")

            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("📄 YAML (RenderCV)")
                st.code(st.session_state.yaml_generated, language="yaml")

                st.download_button(
                    "💾 Descargar YAML",
                    st.session_state.yaml_generated,
                    "cv_optimizado.yaml",
                    "text/yaml",
                    use_container_width=True,
                )

            with col2:
                st.subheader("📄 PDF Visual")
                if st.session_state.pdf_path:
                    # Leer PDF binario para descarga
                    with open(st.session_state.pdf_path, "rb") as f:
                        pdf_bytes = f.read()

                    st.download_button(
                        "📥 Descargar PDF",
                        pdf_bytes,
                        "cv_optimizado.pdf",
                        "application/pdf",
                        type="primary",
                        use_container_width=True,
                    )

                    # Iframe preview (trick para mostrar PDF)
                    import base64

                    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)

            st.divider()

            col_center = st.columns([1, 2, 1])[1]
            with col_center:
                if st.button(
                    "🤖 Continuar al Asistente de Entrevista",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.current_step = 4
                    st.rerun()

                if st.button(
                    "🔄 Generar Otro CV (Reiniciar)", type="secondary", use_container_width=True
                ):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()

# TAB 5: ASISTENTE DE ENTREVISTA
elif st.session_state.current_step == 4:
    st.header("🤖 Asistente de Entrevista con IA")

    st.info(
        "Utiliza este asistente para responder preguntas de postulación o simular una entrevista. La IA responderá como TÚ, usando tu CV y experiencias confirmadas."
    )

    if not st.session_state.cv_text:
        st.warning(
            "⚠️ No hay contexto de CV cargado. Necesitamos tu CV para que el asistente funcione."
        )

        col_up1, col_up2 = st.columns(2)
        with col_up1:
            if st.button("📝 Ir al Inicio para cargar CV"):
                st.session_state.current_step = 0
                st.rerun()

        # Opción rápida de carga ahí mismo (Opcional, pero mejora UX)
        st.divider()
        st.subheader("O carga rápida de contexto:")
        uploaded_file_quick = st.file_uploader(
            "Sube tu CV (PDF) rápidamente:", type=["pdf"], key="quick_uploader"
        )
        if uploaded_file_quick:
            with st.spinner("Procesando..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file_quick.getvalue())
                        tmp_path = tmp_file.name
                    parser = CVParser()
                    cv_data = parser.parse_pdf(tmp_path)
                    st.session_state.cv_text = cv_data.raw_text
                    Path(tmp_path).unlink()
                    st.success("✅ CV cargado. Ya puedes usar el asistente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        # Verificar si hay descripción de vacante
        if not st.session_state.job_description:
            st.warning(
                "⚠️ No hay descripción de vacante cargada. El asistente necesita saber a qué estás postulando."
            )

            st.session_state.job_description = st.text_area(
                "Ingresa la descripción de la vacante / empresa:",
                placeholder="Senior Python Developer at Google...",
                height=150,
            )

            if not st.session_state.job_description:
                st.info("Por favor ingresa la descripción para habilitar el asistente.")
                st.stop()
        else:
            with st.expander("👀 Ver Vacante / Contexto Actual", expanded=False):
                new_desc = st.text_area(
                    "Editar Vacante:", value=st.session_state.job_description, height=150
                )
                if new_desc != st.session_state.job_description:
                    st.session_state.job_description = new_desc
                    st.toast("Contexto de vacante actualizado")

        col_main, col_hist = st.columns([2, 1])

        with col_main:
            st.subheader("Simulador de Respuesta")

            # Input de pregunta
            question_input = st.text_area(
                "Pregunta de la Entrevista / Formulario:",
                placeholder="Ej: ¿Por qué crees que eres el candidato ideal para este puesto?",
                height=100,
            )

            # Selección de Tono
            tone_options = ["Profesional", "Entusiasta", "Conciso", "Técnico", "Persuasivo"]
            selected_tone = st.select_slider(
                "Tono de la respuesta:", options=tone_options, value="Profesional"
            )

            if st.button("✨ Generar Respuesta", type="primary", use_container_width=True):
                if not question_input.strip():
                    st.error("Por favor escribe una pregunta.")
                elif _is_user_blocked():
                    st.error("🚫 Has alcanzado tu limite de uso de IA. Contacta al administrador.")
                else:
                    with st.spinner("🧠 Pensando como tú..."):
                        try:
                            # Inicializar componentes
                            gemini_client = GeminiClient()
                            db = CVDatabase()
                            proxy = InterviewProxy(gemini_client, db)

                            # Generar respuesta
                            answer = proxy.answer_question(
                                question=question_input,
                                cv_text=st.session_state.cv_text,
                                job_description=st.session_state.job_description,
                                tone=selected_tone,
                            )

                            # Registrar tokens consumidos
                            _record_token_usage(gemini_client, "interview_answer")

                            # Mostrar respuesta
                            st.session_state.last_generated_answer = answer
                            st.session_state.last_question = question_input

                            # Guardar en historial DB
                            # Asumimos que el CV actual generado es el último en historial si existe
                            # O podríamos pasar None si no hay asociación directa aún
                            # Para simplificar, guardamos sin link a CV específico por ahora o buscamos el último
                            try:
                                # Intento simple de obtener ID del último CV generado en esta sesión
                                # Esto requeriría haber guardado el ID en session_state en el Tab 4
                                # Como no lo tenemos a mano, pasamos None
                                db.save_interview_session(None, question_input, answer)
                            except Exception as db_e:
                                logger.error(f"No se pudo guardar sesión en DB: {db_e}")

                        except Exception as e:
                            st.error(f"Error generando respuesta: {e}")

            # Mostrar resultado si existe
            if "last_generated_answer" in st.session_state:
                st.divider()
                st.subheader("Respuesta Sugerida:")
                st.info(f"**Pregunta:** {st.session_state.last_question}")

                st.text_area(
                    "Copia tu respuesta:", value=st.session_state.last_generated_answer, height=250
                )

                # Feedback visual
                st.success("✅ Respuesta generada basada en tu perfil real.")

        with col_hist:
            st.subheader("📚 Historial Reciente")
            try:
                db = CVDatabase()
                sessions = db.get_interview_sessions(limit=10)
                if not sessions:
                    st.caption("No hay preguntas recientes.")

                for s in sessions:
                    with st.expander(f"❓ {s['question'][:40]}..."):
                        st.write(s["generated_answer"])
                        st.caption(f"📅 {s['created_at']}")
            except Exception as e:
                st.error("Error cargando historial.")

        st.divider()
        if st.button("🔄 Generar Otro CV (Reiniciar)", type="secondary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# Footer
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: #888; padding: 1rem;'>
    Powered by <strong>Gemini AI</strong> + <strong>RenderCV</strong> | 
    Desarrollado con ❤️ usando Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
