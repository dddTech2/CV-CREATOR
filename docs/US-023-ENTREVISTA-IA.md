# PRD: Asistente de Entrevistas y Postulación con IA (AI Proxy)

## Overview

Este módulo extiende la funcionalidad de la aplicación `cv-app` permitiendo que la IA actúe como un "proxy" del usuario para responder preguntas de postulación o entrevistas escritas. El sistema utilizará una **Base de Conocimiento Unificada** compuesta por el CV original, las respuestas históricas almacenadas en `skill_memory` (recopiladas durante el Gap Analysis), y el CV optimizado generado para la vacante actual.

La meta es que el usuario pueda pegar las preguntas típicas de formularios de aplicación (ej: "¿Por qué quieres trabajar aquí?", "Describe un reto técnico complejo") y obtener respuestas personalizadas y coherentes con su perfil real, sin tener que redactarlas desde cero.

## Goals

-   Permitir al usuario cargar preguntas específicas de una postulación.
-   Generar respuestas en primera persona simulando ser el usuario.
-   Utilizar el contexto histórico (respuestas pasadas) para mantener consistencia.
-   Alinear las respuestas con la estrategia del CV generado para esa vacante específica.
-   Permitir guardar estas sesiones de "simulacro de entrevista" para referencia futura.

## User Stories

### US-023: Backend - Motor de Contexto Unificado
**Description:** Como sistema, necesito consolidar toda la información disponible del usuario para alimentar al "AI Proxy".
**Acceptance Criteria:**
- [ ] Clase `ContextManager` en `src/ai_proxy.py` (nuevo archivo).
- [ ] Método `build_context(user_id, job_description) -> str`.
- [ ] El contexto debe incluir:
    -   Texto del CV Base.
    -   Experiencia reescrita del CV actual (si existe).
    -   Respuestas relevantes de la tabla `skill_memory`.
    -   Descripción de la vacante objetivo.
- [ ] Optimización de tokens (resumir si es muy extenso).

### US-024: Backend - Generador de Respuestas de Entrevista
**Description:** Como usuario, quiero que la IA responda preguntas específicas adoptando mi perfil profesional.
**Acceptance Criteria:**
- [ ] Clase `InterviewProxy` en `src/ai_proxy.py` que herede o use `GeminiClient`.
- [ ] Método `answer_question(question: str, context: str, tone: str) -> str`.
- [ ] Prompt de sistema: "Actúa como el candidato descrito en el contexto. Responde la siguiente pregunta de entrevista para la vacante X...".
- [ ] Soporte para ajuste de tono: "Formal", "Entusiasta", "Conciso".

### US-025: Frontend - Tab "🤖 Asistente de Postulación"
**Description:** Como usuario, quiero una nueva pestaña en la interfaz para gestionar preguntas y respuestas de postulación.
**Acceptance Criteria:**
- [ ] Nuevo Tab 5 en `app.py`: "🤖 Asistente".
- [ ] Área para pegar preguntas (una por línea o texto libre).
- [ ] Selector de tono de respuesta.
- [ ] Botón "Generar Respuestas".
- [ ] Visualización de respuestas generadas con opción de copiar al portapapeles.
- [ ] Integración con el estado actual (`st.session_state.job_description`).

### US-026: Backend - Persistencia de Sesiones
**Description:** Como usuario, quiero que las preguntas y respuestas generadas se guarden asociadas al CV actual.
**Acceptance Criteria:**
- [ ] Nueva tabla `interview_sessions` en `src/database.py`.
- [ ] Campos: `id`, `cv_id` (FK), `question`, `answer`, `created_at`.
- [ ] Métodos CRUD en `CVDatabase`.
- [ ] Visualización de sesiones pasadas en el historial del Sidebar.

## Functional Requirements

**FR-01:** El sistema DEBE priorizar la información confirmada por el usuario (Skill Memory) sobre la información inferida del CV.
**FR-02:** Las respuestas generadas NO DEBEN exceder una longitud razonable para formularios web (ajustable, default ~200 palabras).
**FR-03:** El sistema DEBE detectar si la pregunta es técnica o comportamental y ajustar el estilo de respuesta.
**FR-04:** Si el sistema carece de información para responder verazmente (ej: "Describe tu experiencia con [Herramienta Desconocida]"), DEBE solicitar input al usuario o sugerir una respuesta honesta sobre la falta de experiencia pero disposición a aprender.

## Technical Considerations

### Nueva Estructura de Archivos
```
cv-app/
├── src/
│   ├── ai_proxy.py          # Lógica del Asistente de Entrevista
```

### Prompt Engineering (Borrador)
```text
Eres {user_name}, un profesional con el siguiente perfil:
{cv_context}

Tus experiencias confirmadas y detalles técnicos son:
{skill_memory_context}

Estás postulando a la vacante:
{job_description}

TAREA: Responde la siguiente pregunta de entrevista en primera persona.
Pregunta: "{question}"

Directrices:
- Sé honesto (basa tu respuesta solo en el contexto provisto).
- Usa un tono {selected_tone}.
- Destaca cómo tu experiencia resuelve problemas de la vacante.
```

### Database Schema Updates
```sql
CREATE TABLE IF NOT EXISTS interview_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cv_id INTEGER, -- Link al CV generado para esta vacante
    question TEXT NOT NULL,
    generated_answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cv_id) REFERENCES cv_history(id)
);
```
