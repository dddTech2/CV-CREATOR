[PRD]
# PRD: Generador Inteligente de Hojas de Vida con IA (CV Generator App)

## Overview

Una aplicación Python con backend basado en Gemini AI y frontend en Streamlit que ayuda a usuarios a crear hojas de vida optimizadas para vacantes específicas. El sistema implementa un protocolo de **Gap Analysis** donde la IA analiza las brechas entre el CV actual del usuario y los requisitos de la vacante, hace preguntas estratégicas para llenar esos gaps, y genera un CV en formato YAML compatible con RenderCV que se renderiza como PDF profesional.

La aplicación actúa como un **Estratega de Carrera Senior** que no solo genera CVs, sino que maximiza la compatibilidad del candidato con la vacante mediante un proceso conversacional inteligente.

## Goals

- Maximizar la compatibilidad entre el CV del usuario y los requisitos de la vacante mediante análisis de brechas
- Generar CVs profesionales en formato YAML válido según el estándar de RenderCV
- Proporcionar una interfaz intuitiva con Streamlit que guíe al usuario paso a paso
- Soportar múltiples idiomas para CVs internacionales
- Mantener historial de CVs generados con trazabilidad (DB + archivos)
- Validar completamente el YAML generado y renderizar PDF antes de entregar
- Permitir selección de múltiples temas/plantillas de RenderCV

## Quality Gates

Estos comandos deben pasar para cada user story:
- `pytest tests/ -v` - Suite completa de tests
- `ruff check .` - Linting del código Python
- `ruff format --check .` - Verificación de formato de código

Para user stories de frontend:
- Verificación manual en navegador de la funcionalidad UI

## User Stories

### US-001: Configuración de entorno y estructura base
**Description:** Como desarrollador, necesito la estructura base del proyecto configurada para comenzar el desarrollo.

**Acceptance Criteria:**
- [ ] Archivo `requirements.txt` actualizado con todas las dependencias (streamlit, google-generativeai, rendercv, pyyaml, sqlalchemy, pytest, ruff)
- [ ] Archivo `.env.example` con variables necesarias (GEMINI_API_KEY)
- [ ] Estructura de carpetas: `src/`, `tests/`, `outputs/`, `data/`
- [ ] Archivo `pyproject.toml` con configuración de ruff
- [ ] README.md con instrucciones de instalación y uso

### US-002: Backend - Cliente Gemini AI
**Description:** Como sistema, necesito conectarme a Gemini AI para procesar las solicitudes de generación de CV.

**Acceptance Criteria:**
- [ ] Clase `GeminiClient` en `src/ai_backend.py` que inicializa la conexión con Gemini
- [ ] Método para cargar API key desde `.env`
- [ ] Manejo de errores de conexión y rate limits
- [ ] Tests unitarios para el cliente (con mocking)
- [ ] Configuración de modelo: `gemini-pro` o `gemini-1.5-pro`

### US-003: Backend - Procesador de CV actual
**Description:** Como sistema, necesito extraer y parsear el texto del CV actual del usuario (texto plano o PDF).

**Acceptance Criteria:**
- [ ] Clase `CVParser` en `src/cv_parser.py`
- [ ] Método `parse_text(text: str) -> dict` para texto plano
- [ ] Método `parse_pdf(file_path: str) -> dict` usando PyPDF2 o pdfplumber
- [ ] Extracción estructurada: experiencia, educación, habilidades
- [ ] Tests con CVs de ejemplo

### US-004: Backend - Analizador de vacante
**Description:** Como sistema, necesito extraer requisitos clave de la descripción de vacante.

**Acceptance Criteria:**
- [ ] Clase `JobAnalyzer` en `src/job_analyzer.py`
- [ ] Método que identifica: habilidades técnicas, habilidades blandas, experiencia requerida, idiomas
- [ ] Clasificación de requisitos en "Must-have" vs "Nice-to-have"
- [ ] Integración con Gemini para análisis semántico avanzado
- [ ] Tests con descripciones de vacante reales

### US-005: Backend - Motor de Gap Analysis
**Description:** Como sistema, necesito comparar el CV actual con los requisitos de la vacante e identificar brechas.

**Acceptance Criteria:**
- [ ] Clase `GapAnalyzer` en `src/gap_analyzer.py`
- [ ] Método `analyze(cv_data: dict, job_requirements: dict) -> GapAnalysisResult`
- [ ] Identificación de habilidades faltantes del CV
- [ ] Priorización de gaps según importancia en la vacante
- [ ] Generación de preguntas específicas para cada gap
- [ ] Máximo 2-3 rounds de preguntas iterativas

### US-006: Backend - Generador de preguntas inteligentes
**Description:** Como sistema, necesito generar preguntas estratégicas para el usuario basadas en los gaps identificados.

**Acceptance Criteria:**
- [ ] Clase `QuestionGenerator` en `src/question_generator.py`
- [ ] Método que genera preguntas contextuales (no genéricas)
- [ ] Formato: "La vacante requiere X pero no lo veo en tu CV. ¿Tienes experiencia con X? Si es así, describe brevemente cómo lo has usado."
- [ ] Agrupación de preguntas relacionadas
- [ ] Soporte para preguntas en múltiples idiomas

### US-007: Backend - Reescritor de experiencia laboral
**Description:** Como sistema, necesito reescribir los bullet points de experiencia laboral integrando las nuevas habilidades confirmadas.

**Acceptance Criteria:**
- [ ] Clase `ExperienceRewriter` en `src/experience_rewriter.py`
- [ ] Método que integra nuevas habilidades en la narrativa existente (no solo agregar a lista)
- [ ] Uso de palabras clave de la vacante (ATS optimization)
- [ ] Cuantificación de logros cuando sea posible
- [ ] Preserva la veracidad (no inventa información no confirmada)
- [ ] Tests comparando antes/después del rewrite

### US-008: Backend - Generador YAML para RenderCV
**Description:** Como sistema, necesito generar el archivo YAML en formato válido de RenderCV.

**Acceptance Criteria:**
- [ ] Clase `YAMLGenerator` en `src/yaml_generator.py`
- [ ] Método `generate(cv_data: dict, theme: str, language: str) -> str`
- [ ] Estructura compatible con schema de RenderCV
- [ ] Soporte para temas: sb2nov, classic, moderncv, engineeringresumes
- [ ] Validación sintáctica de YAML generado
- [ ] Tests con datos de ejemplo y verificación de estructura

### US-009: Backend - Validador de YAML contra schema RenderCV
**Description:** Como sistema, necesito validar que el YAML generado cumple con el schema de RenderCV.

**Acceptance Criteria:**
- [ ] Clase `YAMLValidator` en `src/yaml_validator.py`
- [ ] Descargar/incluir schema JSON de RenderCV
- [ ] Validación usando `jsonschema` library
- [ ] Reporte detallado de errores de validación
- [ ] Método `validate(yaml_content: str) -> ValidationResult`
- [ ] Tests con YAMLs válidos e inválidos

### US-010: Backend - Integración con RenderCV para generar PDF
**Description:** Como sistema, necesito renderizar el YAML a PDF usando RenderCV.

**Acceptance Criteria:**
- [ ] Clase `PDFRenderer` en `src/pdf_renderer.py`
- [ ] Instalación de RenderCV como dependencia Python
- [ ] Método `render(yaml_path: str, output_dir: str, theme: str) -> str` que retorna path del PDF
- [ ] Manejo de errores de rendering
- [ ] Limpieza de archivos temporales
- [ ] Tests de integración verificando que se genera el PDF

### US-011: Backend - Base de datos para historial
**Description:** Como sistema, necesito una base de datos SQLite para almacenar historial de CVs generados.

**Acceptance Criteria:**
- [ ] Archivo `src/database.py` con modelos SQLAlchemy
- [ ] Tabla `cv_history`: id, timestamp, user_input, job_description, language, theme, yaml_path, pdf_path, gap_analysis, questions_asked
- [ ] Métodos CRUD: create, read, list, delete
- [ ] Inicialización automática de DB en primera ejecución
- [ ] Tests de operaciones de base de datos

### US-012: Frontend - Página principal con tabs
**Description:** Como usuario, necesito una interfaz con tabs para navegar por el proceso de generación de CV.

**Acceptance Criteria:**
- [ ] Archivo `app.py` como entry point de Streamlit
- [ ] 4 tabs: "📝 Inputs", "🔍 Análisis", "💬 Preguntas", "✅ Resultado"
- [ ] Diseño limpio y profesional con st.set_page_config
- [ ] Logo/título de la aplicación
- [ ] Manejo de estado con st.session_state

### US-013: Frontend - Tab 1: Inputs del usuario
**Description:** Como usuario, quiero proporcionar mi CV actual, descripción de vacante, idioma y tema en una sola pantalla.

**Acceptance Criteria:**
- [ ] Text area grande para pegar CV actual (o file uploader para PDF)
- [ ] Text area para descripción de vacante
- [ ] Selectbox para idioma: Español, English, Português, Français
- [ ] Selectbox para tema de RenderCV con previews/descripciones
- [ ] Botón "Analizar" que valida inputs antes de proceder
- [ ] Validación: todos los campos son requeridos
- [ ] Mensajes de error claros si falta información

### US-014: Frontend - Tab 2: Visualización de Gap Analysis
**Description:** Como usuario, quiero ver el análisis de brechas entre mi CV y la vacante.

**Acceptance Criteria:**
- [ ] Spinner/loading mientras se ejecuta el análisis
- [ ] Sección "Requisitos de la vacante" con badges para must-haves
- [ ] Sección "Habilidades encontradas en tu CV" con checkmarks verdes
- [ ] Sección "Brechas identificadas" con iconos de warning
- [ ] Botón "Continuar a Preguntas" que habilita el tab 3

### US-015: Frontend - Tab 3: Conversación de preguntas iterativas
**Description:** Como usuario, quiero responder preguntas sobre mis habilidades en un formato conversacional.

**Acceptance Criteria:**
- [ ] Interfaz tipo chat mostrando preguntas de la IA
- [ ] Text area para responder cada pregunta
- [ ] Botón "Enviar respuesta" que procesa y puede generar preguntas de seguimiento
- [ ] Indicador de progreso: "Round 1 de 3" o similar
- [ ] Opción "Saltar pregunta" si el usuario no tiene esa habilidad
- [ ] Botón "Generar CV" cuando se completen las preguntas necesarias
- [ ] Historial de preguntas/respuestas visible

### US-016: Frontend - Tab 4: Visualización de resultado y preview PDF
**Description:** Como usuario, quiero ver el YAML generado y el PDF renderizado antes de descargar.

**Acceptance Criteria:**
- [ ] Spinner mientras se genera YAML y PDF
- [ ] Code block con el YAML generado (con syntax highlighting)
- [ ] Botón para copiar YAML al clipboard
- [ ] Preview del PDF usando st.iframe o componente similar
- [ ] Botón de descarga para YAML y PDF
- [ ] Mensaje de confirmación: "CV guardado en historial"
- [ ] Botón "Generar otro CV" que resetea el proceso

### US-017: Frontend - Sidebar con historial de CVs
**Description:** Como usuario, quiero ver mi historial de CVs generados en el sidebar.

**Acceptance Criteria:**
- [ ] Lista de CVs previos en sidebar con timestamp
- [ ] Cada item muestra: fecha, idioma, tema usado
- [ ] Click en un item carga ese CV en tab de resultado
- [ ] Botón de eliminar para cada item del historial
- [ ] Contador: "X CVs generados"
- [ ] Opción "Limpiar todo el historial" con confirmación

### US-018: Backend - Sistema de prompts para Gemini
**Description:** Como sistema, necesito prompts bien estructurados para cada fase del proceso.

**Acceptance Criteria:**
- [ ] Archivo `src/prompts.py` con templates de prompts
- [ ] Prompt para gap analysis con instrucciones específicas
- [ ] Prompt para generación de preguntas con formato consistente
- [ ] Prompt para reescritura de experiencia con guidelines
- [ ] Prompt para generación final de YAML con validación de estructura
- [ ] Variables interpolables: {cv_text}, {job_description}, {language}, {theme}
- [ ] Tests verificando que los prompts se formatean correctamente

### US-019: Manejo de errores y logging
**Description:** Como desarrollador, necesito logs detallados y manejo de errores robusto.

**Acceptance Criteria:**
- [ ] Configuración de logging en `src/logger.py`
- [ ] Logs en archivo: `logs/app.log` con rotación
- [ ] Try-catch en todas las operaciones críticas (API calls, file I/O, DB)
- [ ] Mensajes de error user-friendly en Streamlit
- [ ] Logging de excepciones con traceback completo
- [ ] Rate limiting para API de Gemini

### US-020: Tests end-to-end
**Description:** Como desarrollador, necesito tests que validen el flujo completo de la aplicación.

**Acceptance Criteria:**
- [ ] Test E2E en `tests/test_e2e.py` simulando flujo completo
- [ ] Mock de Gemini API para tests determinísticos
- [ ] Test con CV de ejemplo + vacante → verificar YAML válido y PDF generado
- [ ] Test de validación de errores (inputs inválidos)
- [ ] Test de persistencia en DB
- [ ] Coverage mínimo: 80%

## Functional Requirements

**FR-1:** El sistema DEBE extraer texto de archivos PDF usando bibliotecas Python (PyPDF2 o pdfplumber).

**FR-2:** El sistema DEBE conectarse a Gemini API usando la API key configurada en `.env`.

**FR-3:** El análisis de brechas DEBE identificar al menos 3 categorías: habilidades técnicas, habilidades blandas, y experiencia relevante.

**FR-4:** El sistema DEBE generar entre 3-7 preguntas por round de análisis de brechas.

**FR-5:** El sistema NO DEBE inventar información no confirmada por el usuario.

**FR-6:** El YAML generado DEBE ser validado sintácticamente (PyYAML) antes de pasar a validación de schema.

**FR-7:** El YAML generado DEBE ser validado contra el schema de RenderCV usando jsonschema.

**FR-8:** El sistema DEBE renderizar el PDF usando RenderCV instalado como dependencia Python.

**FR-9:** Los archivos generados (YAML y PDF) DEBEN guardarse en `outputs/{timestamp}/` con estructura: `cv.yaml` y `cv.pdf`.

**FR-10:** El historial DEBE almacenarse tanto en SQLite (`data/cv_history.db`) como en archivos físicos (`outputs/`).

**FR-11:** El frontend DEBE prevenir navegación a tabs subsecuentes si el tab actual no está completo.

**FR-12:** El sistema DEBE soportar los siguientes idiomas: Español, English, Português, Français.

**FR-13:** El sistema DEBE soportar selección de temas de RenderCV: sb2nov, classic, moderncv, engineeringresumes.

**FR-14:** El preview del PDF DEBE mostrarse en un iframe dentro de Streamlit.

**FR-15:** El sistema DEBE manejar rate limits de Gemini API con exponential backoff.

## Non-Goals (Out of Scope)

- ❌ Autenticación multi-usuario (es single-user local)
- ❌ Deployment a cloud o hosting (solo uso local)
- ❌ Edición manual del YAML dentro de la app (usar editor externo)
- ❌ Integración con LinkedIn o plataformas de empleo
- ❌ OCR para CVs escaneados (solo PDFs con texto seleccionable)
- ❌ Sistema de plantillas custom (solo usar las de RenderCV)
- ❌ Traducción automática entre idiomas (el usuario selecciona idioma de salida)
- ❌ Análisis de compatibilidad con ATS (Applicant Tracking Systems) - fase 2
- ❌ Generación de cover letters

## Technical Considerations

### Arquitectura
```
cv-app/
├── src/
│   ├── __init__.py
│   ├── ai_backend.py          # GeminiClient
│   ├── cv_parser.py           # CVParser
│   ├── job_analyzer.py        # JobAnalyzer
│   ├── gap_analyzer.py        # GapAnalyzer
│   ├── question_generator.py  # QuestionGenerator
│   ├── experience_rewriter.py # ExperienceRewriter
│   ├── yaml_generator.py      # YAMLGenerator
│   ├── yaml_validator.py      # YAMLValidator
│   ├── pdf_renderer.py        # PDFRenderer
│   ├── database.py            # DB models y CRUD
│   ├── prompts.py             # Prompt templates
│   └── logger.py              # Logging config
├── tests/
│   ├── __init__.py
│   ├── test_ai_backend.py
│   ├── test_cv_parser.py
│   ├── test_gap_analyzer.py
│   ├── test_yaml_generator.py
│   ├── test_validator.py
│   └── test_e2e.py
├── outputs/                    # CVs generados
├── data/                       # SQLite DB
├── logs/                       # Application logs
├── templates/                  # YAML templates RenderCV
│   └── sb2nov_template.yaml
├── app.py                      # Streamlit frontend
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

### Dependencias principales
- `streamlit>=1.30.0` - Frontend
- `google-generativeai>=0.3.0` - Gemini AI
- `rendercv>=1.9.0` - PDF rendering
- `pyyaml>=6.0` - YAML parsing
- `sqlalchemy>=2.0.0` - ORM
- `pypdf2>=3.0.0` o `pdfplumber>=0.10.0` - PDF parsing
- `jsonschema>=4.20.0` - YAML validation
- `pytest>=7.4.0` - Testing
- `ruff>=0.1.0` - Linting y formatting

### Integración con RenderCV
El sistema usará RenderCV como biblioteca Python:
```python
from rendercv import render_cv
render_cv(yaml_path, output_folder, theme)
```

### Manejo de estado en Streamlit
Usar `st.session_state` para:
- `cv_data`: CV parseado
- `job_requirements`: Requisitos extraídos
- `gap_analysis`: Resultado del análisis
- `conversation_history`: Preguntas/respuestas
- `current_round`: Round actual de preguntas (1-3)
- `yaml_generated`: YAML final
- `pdf_path`: Path del PDF generado

### Prompts para Gemini

**Prompt de Gap Analysis:**
```
Eres un Estratega de Carrera Senior. Analiza el CV y la vacante.

CV del usuario:
{cv_text}

Descripción de vacante:
{job_description}

Tareas:
1. Identifica habilidades técnicas y blandas críticas (must-haves) de la vacante
2. Cruza con el CV y detecta qué NO aparece explícitamente
3. Retorna JSON: {{"must_haves": [...], "found_in_cv": [...], "gaps": [...]}}
```

**Prompt de Generación de Preguntas:**
```
Basado en estos gaps: {gaps}

Genera 3-5 preguntas directas y específicas para confirmar si el usuario tiene experiencia.
Formato: "La vacante requiere [X], pero no lo veo en tu CV. ¿Tienes experiencia con [X]? Si es así, describe brevemente cómo lo has usado."

Retorna JSON: {{"questions": ["...", "..."]}}
```

**Prompt de Reescritura:**
```
CV original: {cv_data}
Nuevas habilidades confirmadas: {confirmed_skills}
Vacante objetivo: {job_description}
Idioma: {language}

Reescribe los bullet points de experiencia laboral INTEGRANDO las nuevas habilidades en la narrativa (no solo listar).
Usa palabras clave de la vacante.
Cuantifica logros cuando sea posible.
NO inventes información no confirmada.

Retorna JSON con estructura de experiencia actualizada.
```

**Prompt de Generación YAML:**
```
Genera el YAML completo para RenderCV siguiendo EXACTAMENTE esta estructura:
[Incluir ejemplo de John_Doe_Sb2novTheme_CV.yaml]

Datos del usuario: {rewritten_cv_data}
Tema: {theme}
Idioma: {language}

CRÍTICO: Valida que el YAML sea sintácticamente correcto y siga el schema de RenderCV.
```

## Success Metrics

**Métricas de calidad:**
- ✅ 100% de YAMLs generados deben pasar validación de schema
- ✅ 100% de YAMLs válidos deben renderizar PDF sin errores
- ✅ 80%+ de code coverage en tests
- ✅ 0 errores de linting (ruff)

**Métricas de UX:**
- ⏱️ Tiempo de generación completa < 2 minutos
- 💬 Promedio de 4-6 preguntas por CV (no abrumar al usuario)
- 📊 Datos guardados correctamente en DB y archivos

**Métricas de robustez:**
- 🔒 Manejo de 100% de errores de API (rate limits, timeouts)
- 🛡️ Validación de inputs antes de procesamiento

## Open Questions

1. ¿Deberíamos incluir un modo "Quick" que genere el CV sin gap analysis para usuarios con prisa?
2. ¿El sistema debe detectar y avisar si el CV resultante es muy largo (>2 páginas)?
3. ¿Deberíamos incluir tips/sugerencias mientras el usuario responde preguntas?
4. ¿Necesitamos exportar el CV a otros formatos además de PDF (DOCX, HTML)?
5. ¿Deberíamos incluir analytics del historial (ej: "Has aplicado a 5 vacantes de Data Science")?

## Next Steps

1. Revisar y aprobar este PRD
2. Crear issues individuales para cada User Story
3. Priorizar US-001 a US-005 como fase 1 (backend core)
4. Setup del entorno de desarrollo
5. Sprint planning para primeras 2 semanas

[/PRD]
