# PRD: Mejora de Navegación y Carga de Historial

## 1. Introducción
**Propósito:** Mejorar la experiencia de usuario (UX) permitiendo la navegación fluida entre los pasos del generador de CV y corrigiendo el flujo de carga desde el historial.
**Alcance:** Frontend (Streamlit) - `app.py`.

## 2. Problema Actual
1. **Bloqueo de Navegación:** Los usuarios no pueden navegar libremente entre las pestañas ("Inputs", "Análisis", "Preguntas", "Resultado") una vez han avanzado. El sistema actual fuerza un flujo lineal estricto sin posibilidad de retroceder o saltar a secciones ya completadas.
2. **Carga de Historial Incompleta:** Al cargar un CV desde el historial, el sistema restaura los datos pero mantiene al usuario en la pantalla actual (generalmente "Inputs" o "Inicio"), mostrando un mensaje "Ve al tab 'Resultado'" que es imposible de obedecer debido al bloqueo de navegación descrito arriba.

## 3. Solución Propuesta

### 3.1 Habilitar Navegación por Pestañas (Tabs)
Convertir la barra de progreso superior en una barra de navegación interactiva.
- **Botones Interactivos:** Cada paso en la barra de progreso funcionará como un botón.
- **Lógica de Acceso:** 
    - Permitir acceso a cualquier paso.
    - Mantener la indicación visual de paso actual y pasos completados.

### 3.2 Redirección Automática al Cargar
Automatizar el cambio de pestaña al recuperar una sesión.
- Al hacer clic en "📂 Cargar" en el historial, el sistema debe actualizar automáticamente `st.session_state.current_step` al índice correspondiente a "Resultado" (3).
- Eliminar la necesidad de que el usuario navegue manualmente tras la carga.

## 4. Criterios de Aceptación
1. **Prueba de Carga:** Al hacer clic en "Cargar" en un ítem del historial, la aplicación debe mostrar inmediatamente la pantalla de "Resultado" con el PDF y YAML correspondientes.
2. **Prueba de Navegación:** El usuario debe poder hacer clic en "Inputs" para volver a editar sus datos, y luego hacer clic en "Resultado" para volver a ver el CV generado, sin perder el estado.

## 5. Cambios Implementados
- **Archivo:** `cv-app/app.py`
- **Navegación:** Se reemplazaron los indicadores estáticos `st.markdown` por `st.button` que actualizan `st.session_state.current_step`.
- **Historial:** Se agregó `st.session_state.current_step = 3` y `st.rerun()` en la lógica de carga del historial.
