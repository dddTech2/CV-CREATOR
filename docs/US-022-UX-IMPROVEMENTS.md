# US-022: Mejoras de Experiencia de Usuario (UX) y Navegación

## Resumen
Mejorar la usabilidad de la aplicación introduciendo controles manuales de navegación entre las secciones de configuración y análisis, y permitiendo la iteración/refinamiento de las respuestas dadas a la IA.

## Problema Actual
1. **Avance Agresivo:** El sistema avanza automáticamente del paso de "Inputs" al de "Análisis" tan pronto como detecta texto en los campos, impidiendo que el usuario configure opciones como el idioma o el tema visual.
2. **Falta de Control:** El usuario no tiene tiempo suficiente para revisar el análisis de brechas antes de ser llevado a las preguntas.
3. **Flujo Unidireccional:** Una vez generado el CV, no existe una forma fácil de regresar a corregir o matizar las respuestas dadas en la entrevista sin reiniciar todo el proceso.

## Requerimientos Funcionales

### 1. Navegación Manual: Inputs -> Análisis
**Cambio:** Desactivar el auto-avance inmediato.
**Comportamiento Nuevo:**
- Validar los inputs (CV y Job Description) en tiempo real.
- Si son válidos, mostrar un mensaje de éxito ("Inputs completos") pero **quedarse en la página**.
- Habilitar un botón principal: `🚀 Comenzar Análisis`.
- Solo avanzar al `Step 1` cuando el usuario haga clic en este botón.

### 2. Navegación Manual: Análisis -> Preguntas
**Cambio:** Permitir lectura pausada del reporte de Gaps.
**Comportamiento Nuevo:**
- Eliminar temporizadores de auto-avance al mostrar los resultados del Gap Analysis.
- Agregar un botón al final del reporte: `💬 Continuar a la Entrevista`.
- Solo avanzar al `Step 2` tras el clic.

### 3. Loop de Iteración: Resultado -> Preguntas
**Cambio:** Permitir refinar el CV.
**Comportamiento Nuevo:**
- En el `Step 3` (Resultado), agregar un botón visible: `✏️ Actualizar Respuestas / Refinar`.
- **Acción del botón:**
    - Regresar el estado a `Step 2` (Preguntas).
    - Marcar `questions_completed = False`.
    - Mantener las `user_answers` existentes en el estado para que aparezcan pre-llenadas (el usuario solo edita lo que quiere cambiar).
    - Al enviar nuevamente las respuestas en el Step 2, el flujo continuará automáticamente al Step 3 para regenerar el CV con la nueva información.

### 4. Mantener Auto-avance: Preguntas -> Resultado
**Restricción:**
- Mantener el comportamiento actual donde, al responder la última pregunta, el sistema pasa automáticamente a la generación del CV sin requerir un clic adicional.

## Criterios de Aceptación
- [ ] El usuario puede pegar su CV y la vacante, y luego cambiar el idioma O el tema SIN que la página cambie automáticamente.
- [ ] El usuario debe hacer clic explícitamente para iniciar el análisis.
- [ ] En la pantalla de resultados finales, existe un botón funcional que permite volver a las preguntas, editar una respuesta y regenerar el CV.
