# US-015: Frontend - Tab 3: Conversación de preguntas iterativas

## 📋 Resumen

**User Story:** Como usuario, quiero responder preguntas sobre mis habilidades en un formato conversacional.

**Estado:** ✅ COMPLETADA

**Fecha:** 25 de enero de 2026

---

## 🎯 Objetivos Completados

✅ **Integración con Backend de Preguntas:**
- Conexión con `QuestionGenerator` y `GeminiClient`
- Generación dinámica de preguntas basadas en los gaps detectados en el Tab 2
- Soporte multilenguaje (ES, EN, PT, FR)

✅ **Interfaz Conversacional (Chat):**
- Chat UI usando `st.chat_message`
- Historial de conversación persistente
- Input de texto para respuestas del usuario
- Botones "Enviar" y "Saltar"

✅ **Flujo de Entrevista:**
- Generación inicial de preguntas (máximo 5)
- Navegación pregunta por pregunta
- Detección de finalización de entrevista
- Guardado de respuestas para uso en la generación del CV

---

## 🏗️ Implementación Técnica

### Flujo de Datos

1. **Input:** `st.session_state.gap_analysis_result` (del Tab 2)
2. **Proceso (Trigger: Entrar al Tab 3):**
   - Inicializa `QuestionGenerator`
   - `generate_questions()` -> Crea lista de `Question`
   - Almacena preguntas en `st.session_state.generated_questions`
3. **Interacción:**
   - Muestra pregunta actual (`current_question_index`)
   - Recibe respuesta del usuario
   - Almacena respuesta en `st.session_state.user_answers`
   - Avanza al siguiente índice
4. **Output:** `st.session_state.user_answers` (Diccionario `skill -> respuesta`)

### Estructura de Datos en Session State

```python
st.session_state.generated_questions = [Question(...), Question(...)]
st.session_state.current_question_index = 0
st.session_state.user_answers = {
    "Docker": "Lo usé en mi último proyecto para...",
    "Kubernetes": "No tengo experiencia"
}
st.session_state.conversation_history = [
    {"role": "ai", "text": "Pregunta 1..."},
    {"role": "user", "text": "Respuesta 1..."},
    ...
]
```

---

## 📸 Características Visuales

### 1. Chat Interactivo
- Mensajes de la IA con icono de asistente
- Mensajes del usuario con icono de usuario
- Formato Markdown soportado

### 2. Formulario de Respuesta
- Text area enfocado en la respuesta
- Botón primario "Enviar Respuesta"
- Botón secundario "Saltar / No tengo experiencia"

### 3. Estado de Finalización
- Mensaje de éxito al completar todas las preguntas
- Resumen desplegable con todas las respuestas recopiladas
- Botón para avanzar al siguiente paso (Generación de CV)

---

## 🧪 Pruebas Realizadas

- [x] Generación de preguntas con Gap Analysis real
- [x] Flujo completo de preguntas (responder todas)
- [x] Opción de saltar preguntas
- [x] Persistencia del historial al cambiar de tab
- [x] Manejo de errores si falla la API

---

## 🚀 Próximos Pasos

- **US-016 (Tab 4: Resultado):** Usar las respuestas recopiladas (`user_answers`) para reescribir el CV y generar el PDF final.
