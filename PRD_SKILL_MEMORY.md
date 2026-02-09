# PRD: Gestor de Memoria de Habilidades (Knowledge Base)

## 1. Introducción
**Propósito:** Permitir al usuario visualizar, editar y gestionar el conocimiento que la IA ha acumulado sobre sus habilidades a través de las sesiones de entrevista.
**Objetivo:** Dar control total al usuario sobre su "perfil de habilidades" persistente, permitiéndole corregir respuestas pasadas o enriquecer descripciones sin tener que esperar a que la IA le vuelva a preguntar.

## 2. Problema Actual
- Las respuestas que el usuario da en el chat se guardan en la base de datos (`skill_memory`), pero son "invisibles" para el usuario hasta que la IA decide preguntar de nuevo por esa habilidad.
- Si el usuario cometió un error tipográfico o quiere mejorar una descripción de experiencia dada en un CV anterior, no tiene una interfaz para hacerlo directamente.

## 3. Solución Propuesta

### 3.1 Nueva Sección: "🧠 Mis Habilidades" (Sidebar)
Implementar un gestor de habilidades en la barra lateral (Sidebar), debajo del historial de CVs.

**Funcionalidades:**
1.  **Visualización:** Listar todas las habilidades (Skills) que tienen una respuesta guardada en la base de datos.
2.  **Edición:** Permitir modificar el texto de la respuesta asociada a cada habilidad.
3.  **Eliminación:** Permitir borrar una habilidad de la memoria si ya no es relevante o fue un error.
4.  **Persistencia:** Al guardar cambios, actualizar directamente la tabla `skill_memory` en SQLite.

### 3.2 Interfaz de Usuario
- **Ubicación:** Sidebar -> Expander "🧠 Mis Habilidades Guardadas".
- **Componentes:**
    - Un `selectbox` o `radio` para seleccionar la habilidad a editar (o una lista desplegable si son muchas).
    - Un `text_area` que muestre la respuesta actual y permita edición.
    - Botones: "💾 Guardar Cambios" y "🗑️ Borrar".

## 4. Historias de Usuario

### US-021: Ver habilidades guardadas
**Como** usuario,
**Quiero** ver una lista de las habilidades que el sistema "sabe" que tengo,
**Para** entender qué información se está reutilizando en mis CVs.

### US-022: Editar respuesta de habilidad
**Como** usuario,
**Quiero** editar el texto de mi experiencia con una habilidad específica (ej. "Python"),
**Para** mejorar la redacción o agregar nuevos logros sin repetir la entrevista.

## 5. Criterios de Aceptación
1.  **Carga de Datos:** El sistema debe cargar todas las entradas de la tabla `skill_memory` al iniciar.
2.  **Edición Exitosa:** Al modificar un texto y guardar, la base de datos debe reflejar el cambio inmediatamente (`UPDATE`).
3.  **Reflejo en Generación:** Si edito una habilidad aquí y luego genero un nuevo CV que requiere esa habilidad, el sistema debe usar la versión editada automáticamente (pre-llenado o uso directo).

## 6. Detalles Técnicos
- **Archivo:** `cv-app/app.py`
- **Métodos DB requeridos:**
    - `db.get_all_skill_answers()` (Ya existe)
    - `db.save_skill_answer()` (Ya existe - funciona como Upsert)
    - `db.delete_skill_answer(skill_name)` (**Nuevo método necesario**)

## 7. Plan de Implementación
1.  Agregar método `delete_skill_answer` en `src/database.py`.
2.  Modificar `app.py` para añadir la sección en el Sidebar.
