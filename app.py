"""
CV Generator App - Generador Inteligente de Hojas de Vida con IA
Frontend principal usando Streamlit
"""
import streamlit as st
import tempfile
import time
from pathlib import Path
import os

from src.logger import get_logger

# Configurar logger
logger = get_logger("frontend")

# Importar módulos del backend
from src.cv_parser import CVParser
from src.job_analyzer import JobAnalyzer
from src.gap_analyzer import GapAnalyzer
from src.question_generator import QuestionGenerator, Language
from src.experience_rewriter import ExperienceRewriter
from src.yaml_generator import YAMLGenerator, ContactInfo, ExperienceEntry, EducationEntry, SkillEntry
from src.pdf_renderer import PDFRenderer
from src.database import CVDatabase
from src.ai_backend import GeminiClient
from src.prompts import PromptManager

# Configuración de la página
st.set_page_config(
    page_title="CV Generator - Estratega de Carrera con IA",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar session_state
if "cv_text" not in st.session_state:
    st.session_state.cv_text = ""
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
st.markdown("""
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
""", unsafe_allow_html=True)

# Header principal
st.markdown('<h1 class="main-header">📄 CV Generator con IA</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Tu estratega de carrera personal impulsado por Gemini AI</p>',
    unsafe_allow_html=True
)

# NUEVO: Barra de progreso global
steps_names = ["📝 Inputs", "🔍 Análisis", "💬 Preguntas", "✅ Resultado"]
current_step_name = steps_names[st.session_state.current_step]
progress_value = (st.session_state.current_step + 1) / len(steps_names)

# Mostrar barra de progreso
st.progress(progress_value)

# Mostrar paso actual con emojis de completado
progress_cols = st.columns(4)
for idx, step_name in enumerate(steps_names):
    with progress_cols[idx]:
        if idx < st.session_state.current_step:
            st.markdown(f"✅ **{step_name}**")
        elif idx == st.session_state.current_step:
            st.markdown(f"🔵 **{step_name}**")
        else:
            st.markdown(f"⚪ {step_name}")

st.divider()

# Sidebar con historial
with st.sidebar:
    st.header("📚 Historial de CVs")
    
    # Inicializar DB
    db = CVDatabase()
    try:
        history = db.get_all_cvs()
    except Exception as e:
        st.error(f"Error leyendo historial: {e}")
        history = []
    
    if not history:
        st.info("No hay CVs generados aún.")
    else:
        st.metric("CVs Generados", len(history))
        
        if st.button("🗑️ Limpiar Historial", type="secondary", use_container_width=True):
            db.clear_all()
            st.rerun()
        
        st.divider()
        
        # Mostrar lista inversa (más recientes arriba) - get_all_cvs ya los trae ordenados
        for cv_item in history:
            # Formatear fecha
            date_str = cv_item['created_at']
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
                    if st.button("📂 Cargar", key=f"load_{cv_item['id']}", use_container_width=True):
                        # Cargar datos completos
                        full_cv = db.get_cv_by_id(cv_item['id'])
                        if full_cv:
                            # Restaurar estado
                            st.session_state.yaml_generated = full_cv['yaml_content']
                            st.session_state.pdf_path = full_cv['pdf_path']
                            st.session_state.questions_completed = True
                            st.session_state.cv_text = full_cv.get('original_cv') or st.session_state.cv_text
                            st.session_state.job_description = full_cv.get('job_description') or st.session_state.job_description
                            
                            st.toast(f"✅ CV cargado: {cv_item['job_title']}")
                            st.info("Ve al tab '✅ Resultado' para ver el CV cargado")
                
                with col_b:
                    if st.button("❌ Borrar", key=f"del_{cv_item['id']}", type="secondary", use_container_width=True):
                        db.delete_cv(cv_item['id'])
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
    
    st.info("💡 **Tip:** Cuanto más detallado sea tu CV, mejor será el análisis y las recomendaciones.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Tu CV Actual")
        cv_input_method = st.radio(
            "¿Cómo quieres proporcionar tu CV?",
            ["Pegar texto", "Subir PDF"],
            horizontal=True
        )
        
        if cv_input_method == "Pegar texto":
            st.session_state.cv_text = st.text_area(
                "Pega aquí el contenido de tu CV actual",
                value=st.session_state.cv_text,
                height=300,
                placeholder="Ejemplo:\n\nJuan Pérez\nSoftware Engineer\njuan@example.com\n\nExperiencia:\n- Company XYZ (2020-2023)\n  Desarrollé aplicaciones web...\n\nEducación:\n- Universidad ABC\n  Ingeniería en Sistemas\n\nHabilidades:\nPython, JavaScript, SQL..."
            )
            
            if st.session_state.cv_text:
                word_count = len(st.session_state.cv_text.split())
                st.caption(f"📊 {word_count} palabras | {len(st.session_state.cv_text)} caracteres")
        else:
            uploaded_file = st.file_uploader(
                "Sube tu CV en PDF",
                type=["pdf"],
                help="El PDF debe tener texto seleccionable (no escaneos)"
            )
            
            if uploaded_file:
                # Detectar cambio de archivo
                file_hash = hash(uploaded_file.getvalue())
                
                # Si es un archivo nuevo o no hay texto extraído, extraer automáticamente
                if st.session_state.last_uploaded_file_hash != file_hash or not st.session_state.cv_text:
                    with st.spinner("📄 Extrayendo texto del PDF automáticamente..."):
                        try:
                            # Guardar archivo temporalmente
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
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
                            disabled=True
                        )
    
    with col2:
        st.subheader("Descripción de la Vacante")
        st.session_state.job_description = st.text_area(
            "Pega aquí la descripción completa de la vacante",
            value=st.session_state.job_description,
            height=300,
            placeholder="Ejemplo:\n\nSenior Python Developer\n\nRequisitos:\n- 5+ años de experiencia con Python\n- Django, Flask\n- PostgreSQL, MongoDB\n- Docker, Kubernetes\n- Liderazgo de equipos\n\nResponsabilidades:\n- Diseñar arquitecturas escalables\n- Mentoría a desarrolladores junior\n- Code reviews..."
        )
        
        if st.session_state.job_description:
            word_count = len(st.session_state.job_description.split())
            st.caption(f"📊 {word_count} palabras | {len(st.session_state.job_description)} caracteres")
    
    st.divider()
    
    # Configuración adicional
    st.subheader("⚙️ Configuración del CV")
    
    col3, col4 = st.columns(2)
    
    with col3:
        # Mapeo de idiomas a códigos
        language_map = {
            "Español": "es",
            "English": "en",
            "Português": "pt",
            "Français": "fr"
        }
        
        selected_lang_display = st.selectbox(
            "🌐 Idioma del CV a generar",
            ["Español", "English", "Português", "Français"],
            index=["Español", "English", "Português", "Français"].index(
                st.session_state.selected_language
            ),
            help="El CV final se generará en este idioma"
        )
        st.session_state.selected_language = selected_lang_display
    
    with col4:
        # Descripciones de temas
        theme_descriptions = {
            "classic": "📘 Classic - Diseño limpio y profesional, ideal para la mayoría de industrias",
            "sb2nov": "💼 Sb2nov - Diseño moderno de dos columnas, perfecto para tech/startups",
            "moderncv": "🎨 ModernCV - Estilo elegante con sidebar, ideal para creativos",
            "engineeringresumes": "⚙️ Engineering - Diseño técnico optimizado para ingenieros"
        }
        
        selected_theme = st.selectbox(
            "🎨 Tema de RenderCV",
            ["classic", "sb2nov", "moderncv", "engineeringresumes"],
            index=["classic", "sb2nov", "moderncv", "engineeringresumes"].index(
                st.session_state.selected_theme
            ),
            format_func=lambda x: theme_descriptions[x],
            help="El tema define el estilo visual de tu CV"
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
        st.button("Continuar (Deshabilitado)", disabled=True)
    else:
        st.success("✅ Inputs válidos. Preparando análisis...")
        # Auto-avance
        import time
        with st.spinner("Avanzando al análisis..."):
            time.sleep(1)
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
        
        with st.spinner("🤖 Analizando tu CV vs. la vacante con Gemini AI..."):
            try:
                # Crear cliente de Gemini
                gemini_client = GeminiClient()
                
                # Inicializar GapAnalyzer con el cliente
                gap_analyzer = GapAnalyzer(gemini_client=gemini_client)
                
                # Ejecutar Gap Analysis
                gap_result = gap_analyzer.analyze(
                    cv_text=st.session_state.cv_text,
                    job_description=st.session_state.job_description
                )
                
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
                    "recommendations": recommendations
                }
                st.session_state.gap_analysis_done = True
                
                st.success("✅ ¡Análisis completado!")
                time.sleep(1) # Pequeña pausa para ver el mensaje
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
                help="Total de habilidades must-have identificadas"
            )
        
        with col2:
            matched_count = len(result.get("found_in_cv", []))
            st.metric(
                "Encontradas en CV",
                matched_count,
                delta=f"+{matched_count}",
                delta_color="normal",
                help="Habilidades que ya tienes en tu CV"
            )
        
        with col3:
            gap_count = len(result.get("gaps", []))
            st.metric(
                "Brechas Detectadas",
                gap_count,
                delta=f"-{gap_count}",
                delta_color="inverse",
                help="Habilidades que faltan en tu CV"
            )
        
        with col4:
            if len(result.get("must_haves", [])) > 0:
                match_percentage = int((matched_count / len(result.get("must_haves", []))) * 100)
            else:
                match_percentage = 0
            
            st.metric(
                "Compatibilidad",
                f"{match_percentage}%",
                help="Porcentaje de requisitos que cumples"
            )
        
        st.divider()
        
        # Requisitos de la vacante
        st.subheader("📋 Requisitos Must-Have de la Vacante")
        
        if result.get("must_haves"):
            # Agrupar en filas de 4
            must_haves = result.get("must_haves", [])
            rows = [must_haves[i:i+4] for i in range(0, len(must_haves), 4)]
            
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
            st.info("💡 Esto puede significar que necesitas reescribir tu CV para resaltar mejor tus habilidades")
        
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
            if recommendations.get('critical'):
                for rec in recommendations['critical']:
                    st.error(f"🚨 {rec}")
                
            # Mostrar recomendaciones importantes
            if recommendations.get('important'):
                for rec in recommendations['important']:
                    st.warning(f"⚠️ {rec}")
                
            # Mostrar sugerencias
            if recommendations.get('nice_to_have'):
                with st.expander("ℹ️ Ver sugerencias adicionales"):
                    for rec in recommendations['nice_to_have']:
                        st.info(rec)
        
        # AUTO-AVANCE AUTOMÁTICO
        st.divider()
        st.success("✅ Análisis presentado. Avanzando a Preguntas...")
        with st.spinner("Preparando entrevista..."):
            time.sleep(3) # Pausa suficiente para leer los resultados principales
            st.session_state.current_step = 2
            st.rerun()

        # Botón para re-analizar (manual override)
        if st.button("🔄 Re-analizar (Reiniciar análisis)", type="secondary"):
            st.session_state.gap_analysis_done = False
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
            with st.spinner("🤖 Generando preguntas estratégicas..."):
                try:
                    # Configurar idioma
                    lang_map = {
                        "Español": Language.SPANISH,
                        "English": Language.ENGLISH,
                        "Português": Language.PORTUGUESE,
                        "Français": Language.FRENCH
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
                        gap_result,
                        max_questions=5,
                        prioritize_critical=True
                    )
                    
                    st.session_state.generated_questions = questions
                    
                    # Iniciar conversación
                    if questions:
                        first_q = questions[0]
                        st.session_state.conversation_history = [{
                            "role": "ai",
                            "text": first_q.text,
                            "question_idx": 0
                        }]
                    else:
                        st.session_state.conversation_history = [{
                            "role": "ai",
                            "text": "¡Tu CV está muy completo! No tengo preguntas adicionales. Puedes proceder a generar tu CV."
                        }]
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
                    user_response = st.text_area(
                        "Tu respuesta:",
                        height=100,
                        placeholder="Ej: Sí, he usado esta tecnología en el proyecto X para..."
                    )
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        submit = st.form_submit_button("📤 Enviar Respuesta", type="primary", use_container_width=True)
                    with col2:
                        skip = st.form_submit_button("⏭️ Saltar / No tengo experiencia", type="secondary", use_container_width=True)
                    
                    if submit or skip:
                        # Guardar respuesta
                        answer_text = user_response if submit and user_response else "No tengo experiencia en esto."
                        
                        # Guardar en diccionario de respuestas
                        skill_name = current_q.gap.skill_name
                        st.session_state.user_answers[skill_name] = answer_text
                        
                        # Agregar a historial
                        st.session_state.conversation_history.append({
                            "role": "user",
                            "text": answer_text
                        })
                        
                        # Avanzar
                        next_idx = idx + 1
                        st.session_state.current_question_index = next_idx
                        
                        if next_idx < len(st.session_state.generated_questions):
                            next_q = st.session_state.generated_questions[next_idx]
                            st.session_state.conversation_history.append({
                                "role": "ai",
                                "text": next_q.text,
                                "question_idx": next_idx
                            })
                        else:
                            st.session_state.questions_completed = True
                            st.session_state.conversation_history.append({
                                "role": "ai",
                                "text": "✅ ¡Gracias! He recopilado toda la información necesaria. Generando tu CV automáticamente..."
                            })
                        
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
        if not st.session_state.yaml_generated:
            # AUTO-GENERACIÓN
            try:
                logger.info("Iniciando generación automática de CV (Tab 4)")
                
                # Inicializar clientes
                gemini_client = GeminiClient()
                
                # Mapeo de idioma (definir temprano para usar en todos los prompts)
                lang_code = {
                    "Español": "es", "English": "en", 
                    "Português": "pt", "Français": "fr"
                }.get(st.session_state.selected_language, "es")
                
                language_name = "English" if lang_code == "en" else "Español"
                
                # 1. Estructurar Datos del CV (Contacto, Educación, Experiencia, Skills)
                with st.spinner("🧠 Estructurando información del CV..."):
                    logger.info("Estructurando información del CV...")
                    prompt = PromptManager.get_data_structuring_prompt(
                        st.session_state.cv_text,
                        language=language_name
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
                    logger.info(f"Datos estructurados: {len(structured_data.get('experience', []))} experiencias encontradas")
                
                # 2. Clasificar y Procesar Respuestas del Usuario
                gap_result = st.session_state.gap_analysis_result["gap_analysis"]
                user_answers = st.session_state.user_answers
                
                # Inicializar listas para clasificaciones
                experience_enrichments = []  # Para enriquecer experiencia laboral existente
                projects_to_create = []  # Para crear sección de proyectos
                
                if user_answers:
                    with st.spinner("🔍 Clasificando tus respuestas..."):
                        logger.info("Clasificando respuestas del usuario...")
                        
                        # Obtener nombres de empresas conocidas del CV
                        known_companies = [exp.get("company", "") for exp in structured_data.get("experience", [])]
                        
                        # Clasificar cada respuesta
                        for skill_name, user_answer in user_answers.items():
                            # Skip si no tiene experiencia
                            if "no tengo experiencia" in user_answer.lower():
                                continue
                            
                            # Llamar al clasificador
                            classifier_prompt = PromptManager.get_user_response_classifier_prompt(
                                skill_name=skill_name,
                                user_answer=user_answer,
                                known_companies=known_companies
                            )
                            
                            classifier_response = gemini_client.generate(classifier_prompt)
                            classifier_text = classifier_response.text.strip()
                            
                            # Limpiar JSON
                            if "```json" in classifier_text:
                                classifier_text = classifier_text.split("```json")[1].split("```")[0].strip()
                            elif "```" in classifier_text:
                                classifier_text = classifier_text.split("```")[1].split("```")[0].strip()
                            
                            try:
                                classification = json.loads(classifier_text)
                                
                                if classification["classification"] == "EXPERIENCIA_LABORAL":
                                    experience_enrichments.append({
                                        "skill": skill_name,
                                        "company": classification.get("company_name"),
                                        "description": classification.get("description")
                                    })
                                    logger.info(f"{skill_name} clasificado como EXPERIENCIA_LABORAL en {classification.get('company_name')}")
                                
                                elif classification["classification"] in ["PROYECTO_ACADEMICO", "PROYECTO_PERSONAL"]:
                                    projects_to_create.append({
                                        "skill": skill_name,
                                        "project_name": classification.get("project_name"),
                                        "project_type": classification["classification"],
                                        "description": classification.get("description")
                                    })
                                    logger.info(f"{skill_name} clasificado como {classification['classification']}: {classification.get('project_name')}")
                            
                            except json.JSONDecodeError as e:
                                logger.warning(f"Error al parsear clasificación para {skill_name}: {e}")
                                continue
                
                # 2.1 Enriquecer Experiencia Laboral
                if experience_enrichments and structured_data.get("experience"):
                    with st.spinner("✍️ Enriqueciendo experiencia laboral..."):
                        logger.info("Enriqueciendo experiencia laboral...")
                        
                        # Agrupar enriquecimientos por empresa
                        enrichments_by_company = {}
                        for enrichment in experience_enrichments:
                            company = enrichment["company"]
                            if company not in enrichments_by_company:
                                enrichments_by_company[company] = []
                            enrichments_by_company[company].append(enrichment)
                        
                        # Obtener keywords de la vacante
                        job_keywords = [s.name for s in gap_result.job_requirements.get_must_haves()]
                        
                        # Enriquecer cada experiencia que tenga enriquecimientos
                        for exp in structured_data["experience"]:
                            company_name = exp.get("company", "")
                            
                            # Si esta empresa tiene enriquecimientos
                            if company_name in enrichments_by_company:
                                # Construir highlights actuales
                                current_highlights = "\n".join([f"- {h}" for h in exp.get("highlights", [])])
                                
                                # Construir skills a agregar
                                skills_to_add = "\n".join([
                                    f"- {e['skill']}: {e['description']}"
                                    for e in enrichments_by_company[company_name]
                                ])
                                
                                # Generar prompt de enriquecimiento
                                enrichment_prompt = PromptManager.get_experience_enrichment_prompt(
                                    position=exp.get("position", ""),
                                    company=company_name,
                                    duration=f"{exp.get('start_date', '')} - {exp.get('end_date', '')}",
                                    current_highlights=current_highlights,
                                    user_confirmed_skills=skills_to_add,
                                    job_keywords=job_keywords,
                                    language=language_name
                                )
                                
                                # Llamar a la IA para enriquecer
                                enrichment_response = gemini_client.generate(enrichment_prompt)
                                enriched_text = enrichment_response.text.strip()
                                
                                # Limpiar y convertir a lista
                                enriched_highlights = [
                                    line.strip().lstrip("-").lstrip("•").lstrip("*").strip()
                                    for line in enriched_text.split("\n")
                                    if line.strip() and not line.strip().startswith("#")
                                ]
                                
                                # Actualizar highlights
                                exp["highlights"] = enriched_highlights
                                logger.info(f"Experiencia enriquecida en {company_name}: {len(enriched_highlights)} highlights")
                
                # 2.2 Crear Sección de Proyectos
                if projects_to_create:
                    with st.spinner("🚀 Generando sección de proyectos..."):
                        logger.info("Generando sección de proyectos...")
                        
                        projects = []
                        for project_data in projects_to_create:
                            # Generar entrada de proyecto
                            project_prompt = PromptManager.get_project_entry_generation_prompt(
                                project_name=project_data["project_name"],
                                project_type="académico" if "ACADEMICO" in project_data["project_type"] else "personal",
                                main_skill=project_data["skill"],
                                user_description=project_data["description"],
                                language=language_name
                            )
                            
                            project_response = gemini_client.generate(project_prompt)
                            project_text = project_response.text.strip()
                            
                            # Limpiar JSON
                            if "```json" in project_text:
                                project_text = project_text.split("```json")[1].split("```")[0].strip()
                            elif "```" in project_text:
                                project_text = project_text.split("```")[1].split("```")[0].strip()
                            
                            try:
                                project_entry = json.loads(project_text)
                                projects.append({
                                    "name": project_data["project_name"],
                                    "summary": project_entry.get("summary"),
                                    "start_date": None,
                                    "end_date": None,
                                    "highlights": project_entry.get("highlights", [])
                                })
                                logger.info(f"Proyecto creado: {project_data['project_name']}")
                            except json.JSONDecodeError as e:
                                logger.warning(f"Error al parsear proyecto {project_data['project_name']}: {e}")
                        
                        # Agregar proyectos a structured_data
                        if projects:
                            structured_data["projects"] = projects
                            logger.info(f"Total de proyectos creados: {len(projects)}")

                
                # 2.5. Generar Resumen Profesional Enfocado al Cargo
                with st.spinner("✍️ Generando resumen profesional enfocado al cargo..."):
                    logger.info("Generando resumen profesional...")
                    
                    # Preparar datos para el resumen
                    education_summary = ", ".join([f"{e.get('degree', 'N/A')} en {e.get('institution', 'N/A')}" for e in structured_data.get("education", [])])
                    experience_summary = ", ".join([f"{e.get('position', 'N/A')} en {e.get('company', 'N/A')}" for e in structured_data.get("experience", [])])
                    skills_summary = ", ".join([s.get('details', '') for s in structured_data.get("skills", [])])
                    
                    # Calcular años de experiencia aproximados
                    years_exp = "2-3 años"  # Default
                    if structured_data.get("experience"):
                        try:
                            # Intentar calcular años desde la primera experiencia
                            first_exp = structured_data["experience"][0]
                            start = first_exp.get("start_date", "2020")
                            if start and len(start) >= 4:
                                start_year = int(start[:4])
                                current_year = 2026
                                years_exp = f"{current_year - start_year} años"
                        except:
                            pass
                    
                    # Obtener must-haves del gap analysis
                    must_haves = "\n".join([f"- {s}" for s in st.session_state.gap_analysis_result.get("must_haves", [])])
                    
                    # Generar resumen con IA
                    summary_prompt = PromptManager.get_summary_generation_prompt(
                        job_description=st.session_state.job_description,
                        education_summary=education_summary,
                        experience_summary=experience_summary,
                        skills_summary=skills_summary,
                        years_experience=years_exp,
                        must_have_skills=must_haves,
                        language=language_name
                    )
                    
                    summary_response = gemini_client.generate(summary_prompt)
                    generated_summary = summary_response.text.strip()
                    
                    # Limpiar si viene con markdown o quotes
                    if generated_summary.startswith('"') and generated_summary.endswith('"'):
                        generated_summary = generated_summary[1:-1]
                    
                    # Reemplazar el resumen en structured_data
                    structured_data["summary"] = generated_summary
                    logger.info(f"Resumen generado: {generated_summary[:100]}...")
                
                # 2.75. Priorizar Habilidades según el Cargo
                with st.spinner("🎯 Priorizando habilidades según el cargo..."):
                    logger.info("Priorizando habilidades...")
                    
                    # Preparar habilidades actuales como texto
                    current_skills_text = json.dumps(structured_data.get("skills", []), ensure_ascii=False, indent=2)
                    
                    # Obtener must-haves
                    must_haves_list = st.session_state.gap_analysis_result.get("must_haves", [])
                    must_haves_text = ", ".join(must_haves_list)
                    
                    # Extraer job title de la descripción (o usar genérico)
                    job_title = "Desarrollador Python"  # TODO: Extraer del job_description
                    
                    # Llamar al prompt de priorización
                    skill_prioritization_prompt = PromptManager.get_skill_prioritization_prompt(
                        current_skills=current_skills_text,
                        must_have_skills=must_haves_text,
                        job_title=job_title
                    )
                    
                    prioritization_response = gemini_client.generate(skill_prioritization_prompt)
                    prioritized_skills_text = prioritization_response.text.strip()
                    
                    # Limpiar JSON
                    if "```json" in prioritized_skills_text:
                        prioritized_skills_text = prioritized_skills_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in prioritized_skills_text:
                        prioritized_skills_text = prioritized_skills_text.split("```")[1].split("```")[0].strip()
                    
                    # Parsear y reemplazar
                    try:
                        prioritized_skills = json.loads(prioritized_skills_text)
                        structured_data["skills"] = prioritized_skills
                        logger.info(f"Habilidades priorizadas: {len(prioritized_skills)} categorías")
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error al parsear habilidades priorizadas: {e}, usando originales")
                        
                # 3. Generar YAML
                with st.spinner("📄 Generando archivo YAML..."):
                    logger.info("Generando YAML...")
                    yaml_gen = YAMLGenerator()
                    
                    yaml_content = yaml_gen.parse_and_generate(
                        structured_data=structured_data,
                        theme=st.session_state.selected_theme,
                        language=lang_code
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
                        job_title="CV Generado", # TODO: Extraer título real
                        yaml_content=yaml_content,
                        company="N/A",
                        language=lang_code,
                        theme=st.session_state.selected_theme,
                        pdf_path=pdf_path,
                        original_cv=st.session_state.cv_text,
                        job_description=st.session_state.job_description
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
                    use_container_width=True
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
                        use_container_width=True
                    )
                    
                    # Iframe preview (trick para mostrar PDF)
                    import base64
                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
            
            st.divider()
            
            col_center = st.columns([1, 2, 1])[1]
            with col_center:
                if st.button("🔄 Generar Otro CV (Reiniciar)", type="secondary", use_container_width=True):
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
    unsafe_allow_html=True
)
