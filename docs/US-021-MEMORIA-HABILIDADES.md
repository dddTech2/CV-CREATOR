# US-021: Sistema de Memoria de Habilidades (Skill Memory)

## 1. Resumen
Implementar un sistema de persistencia que almacene las respuestas del usuario sobre sus habilidades (gaps) generadas durante las entrevistas de la IA. El objetivo es que, al crear futuros CVs para otras vacantes, el sistema reconozca si una habilidad faltante ya fue justificada o explicada anteriormente, permitiendo al usuario reutilizar o refinar esa respuesta en lugar de escribirla desde cero.

## 2. Problemática Actual
Actualmente, si un usuario se postula a dos vacantes diferentes que requieren "Liderazgo" (y esta habilidad no está explícita en su CV original), el sistema le preguntará por "Liderazgo" en ambas ocasiones. El usuario debe redactar la respuesta dos veces, lo cual es ineficiente y repetitivo.

## 3. Solución Propuesta
Crear una tabla de "Memoria de Habilidades" en la base de datos local.
*   **Al guardar:** Cada vez que el usuario responde una pregunta sobre una habilidad, se guarda/actualiza en esta memoria.
*   **Al consultar:** Antes de generar las preguntas para una nueva vacante, el sistema verifica si ya existen respuestas para los "gaps" detectados.
*   **Interacción:** Si existe una respuesta previa, se muestra pre-llenada en la interfaz para que el usuario la valide o edite.

## 4. Requerimientos Funcionales

### FR-01: Persistencia de Respuestas
*   El sistema DEBE almacenar las respuestas del usuario asociadas al nombre de la habilidad normalizado (ej: "python", "gestión de proyectos").
*   Se debe guardar el texto de la respuesta y la fecha de última actualización.

### FR-02: Detección de Respuestas Previas
*   Durante la fase de generación de preguntas, el sistema DEBE consultar la base de datos para ver si los *gaps* identificados tienen correspondencia en la memoria.

### FR-03: Interfaz de Reutilización (Streamlit)
*   Si se encuentra una respuesta previa, el campo de texto (`text_area`) de la pregunta DEBE aparecer pre-llenado con dicha respuesta.
*   Debe mostrarse un indicador visual (ej: "💡 Respuesta recuperada de tu historial") para informar al usuario.
*   El usuario DEBE poder editar el texto antes de confirmar.

### FR-04: Actualización de Memoria
*   Si el usuario edita una respuesta recuperada y la envía, el sistema DEBE actualizar la entrada en la base de datos con el nuevo contenido y fecha.

## 5. Cambios Técnicos (Technical Specs)

### A. Base de Datos (`src/database.py`)
Nueva tabla `skill_memory`:
```sql
CREATE TABLE skill_memory (
    skill_name TEXT PRIMARY KEY,  -- Nombre normalizado (lowercase)
    answer_text TEXT NOT NULL,    -- La respuesta del usuario
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 1
);
```

Métodos nuevos en `CVDatabase`:
*   `save_skill_answer(skill_name, answer_text)`: Insert or Replace.
*   `get_skill_answer(skill_name)`: Retorna la respuesta si existe.

### B. Lógica de Negocio (`app.py`)
*   **Normalización:** Implementar lógica para normalizar skills (lowercase, strip).
*   **Flujo en `app.py`:**
    *   Al cargar el Tab 3 (Preguntas): Iterar sobre `generated_questions`. Para cada una, consultar `db.get_skill_answer()`.
    *   Si hay *hit*, guardar en un estado temporal `prefilled_answers`.
    *   Al renderizar el `text_area`, usar `value=prefilled_answers.get(skill)`.
    *   Al enviar la respuesta, llamar a `db.save_skill_answer()`.
