[PRD]
# PRD: Tracking de Tokens, Costos y Panel de Administracion

## Overview

Implementar un sistema completo de tracking de consumo de tokens de IA por usuario, calcular costos basados en precios de Gemini 3 Pro Preview (aunque el modelo real usado sea `gemini-3-flash-preview`), establecer un limite de gasto de 1500 COP por usuario para la demo, y crear un panel de administracion en una pagina separada de Streamlit donde el admin pueda activar/desactivar usuarios y gestionar sus limites.

### Precios de Facturacion (Gemini 3 Pro Preview)
- **Input:** $2.00 USD / 1M tokens
- **Output (incluye thinking tokens):** $12.00 USD / 1M tokens
- **TRM fijo:** 4200 COP/USD (hardcodeado)
- **Limite por usuario (demo):** 1500 COP

### Conversion a COP
- Costo input por token: $0.000002 USD = $0.0084 COP
- Costo output por token: $0.000012 USD = $0.0504 COP

## Goals

- Registrar cada llamada a Gemini con tokens de input y output consumidos
- Calcular el costo en COP para cada operacion y acumulado por usuario
- Mostrar historial de tokens detallado por operacion y agrupado por hoja de vida
- Bloquear al usuario cuando alcance el limite de 1500 COP
- Crear panel de administracion separado para gestionar usuarios
- Implementar log completo de auditoria de activaciones/desactivaciones
- Al reactivar un usuario: resetear contador de tokens pero preservar datos (CVs, skills, entrevistas)

## Quality Gates

Estos comandos deben pasar para cada user story:
- `pytest tests/ -v` - Tests unitarios
- `ruff check .` - Linting
- `ruff format --check .` - Formato de codigo
- `mypy src/ --ignore-missing-imports` - Type checking

## User Stories

### US-TK-001: Esquema de base de datos para tracking de tokens

**Description:** Como desarrollador, quiero crear las tablas necesarias en Supabase para almacenar el consumo de tokens y la auditoria de usuarios.

**Acceptance Criteria:**
- [ ] Crear migracion `supabase/migrations/004_token_tracking.sql`
- [ ] Tabla `token_usage` con columnas:
  - `id SERIAL PRIMARY KEY`
  - `user_id UUID NOT NULL REFERENCES auth.users(id)`
  - `cv_id INTEGER REFERENCES cv_history(id) ON DELETE SET NULL` (nullable, para operaciones no asociadas a un CV)
  - `operation TEXT NOT NULL` (valores: 'gap_analysis', 'question_generation', 'experience_rewrite', 'yaml_generation', 'summary_generation', 'skill_extraction', 'interview_proxy', 'classification', 'other')
  - `input_tokens INTEGER NOT NULL DEFAULT 0`
  - `output_tokens INTEGER NOT NULL DEFAULT 0`
  - `input_cost_cop NUMERIC(10,4) NOT NULL DEFAULT 0`
  - `output_cost_cop NUMERIC(10,4) NOT NULL DEFAULT 0`
  - `total_cost_cop NUMERIC(10,4) NOT NULL DEFAULT 0`
  - `model_used TEXT NOT NULL DEFAULT 'gemini-3-flash-preview'`
  - `created_at TIMESTAMPTZ DEFAULT NOW()`
- [ ] Tabla `user_audit_log` con columnas:
  - `id SERIAL PRIMARY KEY`
  - `user_id UUID NOT NULL REFERENCES auth.users(id)`
  - `admin_id UUID NOT NULL REFERENCES auth.users(id)`
  - `action TEXT NOT NULL CHECK (action IN ('activate', 'deactivate'))`
  - `tokens_at_action INTEGER DEFAULT 0` (tokens acumulados al momento de la accion)
  - `cost_at_action_cop NUMERIC(10,4) DEFAULT 0` (costo acumulado al momento)
  - `notes TEXT`
  - `created_at TIMESTAMPTZ DEFAULT NOW()`
- [ ] Indices: `token_usage(user_id, created_at)`, `token_usage(cv_id)`, `user_audit_log(user_id)`
- [ ] RLS: usuarios pueden leer su propio `token_usage`, admins pueden leer todo
- [ ] RLS: solo admins pueden leer/escribir `user_audit_log`

### US-TK-002: Modulo de tracking de tokens en el backend

**Description:** Como desarrollador, quiero un modulo que registre automaticamente el consumo de tokens en cada llamada a Gemini.

**Acceptance Criteria:**
- [ ] Crear archivo `src/token_tracker.py` con clase `TokenTracker`
- [ ] Constantes de precios: `INPUT_PRICE_USD_PER_M = 2.00`, `OUTPUT_PRICE_USD_PER_M = 12.00`, `TRM_COP_USD = 4200`, `USER_LIMIT_COP = 1500`
- [ ] Metodo `record_usage(user_id, operation, input_tokens, output_tokens, cv_id=None) -> TokenRecord` que calcule costos y guarde en DB
- [ ] Metodo `get_user_total_cost(user_id) -> float` que retorne el costo acumulado en COP
- [ ] Metodo `get_user_remaining(user_id) -> float` que retorne COP restantes (1500 - acumulado)
- [ ] Metodo `is_user_blocked(user_id) -> bool` que retorne `True` si el usuario excedio el limite
- [ ] Metodo `get_usage_by_cv(user_id, cv_id) -> list[TokenRecord]` que retorne detalle por CV
- [ ] Metodo `get_usage_summary_by_cv(user_id) -> list[CVUsageSummary]` que retorne resumen agrupado por CV
- [ ] Metodo `get_usage_history(user_id, limit=50) -> list[TokenRecord]` que retorne historial detallado
- [ ] Metodo `reset_user_tokens(user_id) -> int` que elimine registros de `token_usage` para el usuario (se usa al reactivar)
- [ ] Dataclass `TokenRecord` con: `operation, input_tokens, output_tokens, input_cost_cop, output_cost_cop, total_cost_cop, model_used, created_at, cv_id`
- [ ] Dataclass `CVUsageSummary` con: `cv_id, job_title, total_input_tokens, total_output_tokens, total_cost_cop, operations_count, last_used`

### US-TK-003: Modificar GeminiClient para capturar tokens

**Description:** Como desarrollador, quiero que `GeminiClient` capture y retorne la cantidad de tokens usados en cada llamada.

**Acceptance Criteria:**
- [ ] Modificar `GeminiResponse` dataclass en `src/ai_backend.py` para agregar campos: `input_tokens: int = 0`, `output_tokens: int = 0`
- [ ] En el metodo `generate()`, extraer `usage_metadata` de la respuesta de Gemini: `response.usage_metadata.prompt_token_count` y `response.usage_metadata.candidates_token_count`
- [ ] Asignar los valores de tokens a `GeminiResponse.input_tokens` y `GeminiResponse.output_tokens`
- [ ] Si `usage_metadata` no esta disponible, usar valores 0 y loggear warning
- [ ] Los tests existentes de `test_ai_backend.py` deben seguir pasando

### US-TK-004: Integrar tracking en cada operacion de app.py

**Description:** Como desarrollador, quiero que cada operacion de IA en `app.py` registre automaticamente los tokens consumidos.

**Acceptance Criteria:**
- [ ] Instanciar `TokenTracker` al inicio de la sesion
- [ ] Registrar tokens en operacion `gap_analysis` (linea ~494 de app.py, llamada a `GapAnalyzer`)
- [ ] Registrar tokens en operacion `question_generation` (linea ~716, llamada a `QuestionGenerator`)
- [ ] Registrar tokens en operacion `experience_rewrite` (lineas ~911, ~1029, ~1042, llamadas a `gemini_client.generate`)
- [ ] Registrar tokens en operacion `classification` (linea ~953, classifier prompt)
- [ ] Registrar tokens en operacion `summary_generation` (linea ~1071)
- [ ] Registrar tokens en operacion `skill_extraction` (linea ~1085)
- [ ] Registrar tokens en operacion `interview_proxy` (linea ~1320)
- [ ] Asociar `cv_id` cuando la operacion esta vinculada a un CV especifico
- [ ] Antes de cada operacion de IA, verificar `is_user_blocked(user_id)`. Si esta bloqueado, mostrar `st.error("Has alcanzado el limite de uso de la demo (1500 COP). Contacta al administrador para reactivar tu cuenta.")` y no ejecutar la llamada

### US-TK-005: Vista de consumo de tokens para el usuario

**Description:** Como usuario, quiero ver cuanto he consumido en tokens y cuanto me queda disponible.

**Acceptance Criteria:**
- [ ] Agregar seccion "Consumo de Tokens" en el sidebar de la app, debajo del email del usuario
- [ ] Mostrar barra de progreso con COP consumidos / 1500 COP (cambiar color a rojo cuando >= 80%)
- [ ] Mostrar texto: "Consumido: $XXX.XX COP de $1,500.00 COP"
- [ ] Mostrar texto: "Disponible: $XXX.XX COP"
- [ ] Agregar un expander "Detalle por Hoja de Vida" en el sidebar o en un tab nuevo
- [ ] En el detalle por CV: mostrar tabla con columnas `Titulo Vacante | Operaciones | Tokens Input | Tokens Output | Costo COP`
- [ ] Agregar un expander "Historial Detallado" que muestre las ultimas 50 operaciones
- [ ] En historial detallado: tabla con columnas `Fecha | Operacion | Input Tokens | Output Tokens | Costo COP | CV Asociado`
- [ ] Si el usuario esta bloqueado, mostrar banner rojo permanente en la parte superior de la app
- [ ] Actualizar los datos del sidebar despues de cada operacion de IA (usar `st.rerun()` o recalcular)

### US-TK-006: Panel de administracion - Pagina separada

**Description:** Como administrador, quiero una pagina separada de Streamlit para gestionar usuarios.

**Acceptance Criteria:**
- [ ] Crear archivo `admin_app.py` como aplicacion Streamlit independiente
- [ ] Proteger con login: solo usuarios con `role='admin'` pueden acceder
- [ ] Si un usuario no-admin intenta acceder, mostrar "Acceso denegado. Solo administradores."
- [ ] Agregar instrucciones en README para ejecutar: `streamlit run admin_app.py --server.port 8502`
- [ ] El admin debe autenticarse con sus credenciales de Supabase Auth

### US-TK-007: Panel de admin - Lista y gestion de usuarios

**Description:** Como administrador, quiero ver todos los usuarios registrados y poder activarlos/desactivarlos.

**Acceptance Criteria:**
- [ ] Mostrar tabla con todos los usuarios: `Email | Nombre | Rol | Estado (Activo/Inactivo) | Tokens Consumidos | Costo Total COP | Fecha Registro`
- [ ] Filtros: por estado (Activos/Inactivos/Todos), por rol (User/Admin/Todos)
- [ ] Boton "Desactivar" junto a cada usuario activo que:
  - Cambie `is_active` a `false` en `user_profiles`
  - Registre la accion en `user_audit_log` con `tokens_at_action` y `cost_at_action_cop`
  - Muestre confirmacion antes de desactivar
- [ ] Boton "Activar" junto a cada usuario inactivo que:
  - Cambie `is_active` a `true` en `user_profiles`
  - Ejecute `reset_user_tokens(user_id)` para borrar historial de tokens consumidos (NO borrar CVs, skills, ni entrevistas)
  - Registre la accion en `user_audit_log`
  - Muestre confirmacion antes de activar
- [ ] Columna "Acciones" con los botones correspondientes al estado
- [ ] Metricas generales en la parte superior: Total usuarios, Usuarios activos, Usuarios bloqueados por limite, Costo total de la plataforma

### US-TK-008: Panel de admin - Log de auditoria

**Description:** Como administrador, quiero ver el historial completo de activaciones/desactivaciones de cada usuario.

**Acceptance Criteria:**
- [ ] Seccion "Log de Auditoria" en el panel de admin
- [ ] Tabla con columnas: `Fecha | Usuario | Accion (Activar/Desactivar) | Admin que ejecuto | Tokens al momento | Costo al momento COP | Notas`
- [ ] Filtrar por usuario especifico
- [ ] Filtrar por tipo de accion (Activar/Desactivar/Todas)
- [ ] Filtrar por rango de fechas
- [ ] Ordenar por fecha descendente (mas reciente primero)
- [ ] Campo de "Notas" opcional que el admin puede agregar al activar/desactivar

### US-TK-009: Panel de admin - Detalle de usuario

**Description:** Como administrador, quiero ver el detalle completo de consumo de un usuario especifico.

**Acceptance Criteria:**
- [ ] Al hacer clic en un usuario de la tabla, mostrar vista de detalle
- [ ] Mostrar perfil del usuario: email, nombre, rol, estado, fecha de registro
- [ ] Mostrar resumen de consumo: tokens totales, costo total COP, numero de CVs generados
- [ ] Mostrar tabla de consumo por CV (igual que la vista del usuario pero para el admin)
- [ ] Mostrar historial detallado de operaciones
- [ ] Mostrar log de auditoria filtrado por ese usuario
- [ ] Boton de activar/desactivar desde el detalle

### US-TK-010: Tests de tracking y administracion

**Description:** Como desarrollador, quiero tests que verifiquen el tracking de tokens y las operaciones de administracion.

**Acceptance Criteria:**
- [ ] Crear `tests/test_token_tracker.py`
- [ ] Test de `record_usage()` con calculo correcto de costos en COP
- [ ] Test de `get_user_total_cost()` sumando multiples operaciones
- [ ] Test de `is_user_blocked()` cuando el usuario excede 1500 COP
- [ ] Test de `is_user_blocked()` cuando el usuario no excede el limite
- [ ] Test de `reset_user_tokens()` que verifica que borra tokens pero no datos de CVs
- [ ] Test de calculo de costos: 1000 input tokens + 100 output tokens = (1000 * 0.000002 * 4200) + (100 * 0.000012 * 4200) = 0.0084 + 0.0504 = 13.44 COP... verificar formula
- [ ] Test de `get_usage_summary_by_cv()` con agrupacion correcta
- [ ] Crear `tests/test_admin.py`
- [ ] Test de activacion de usuario (reset tokens, cambio estado, log de auditoria)
- [ ] Test de desactivacion de usuario (cambio estado, log de auditoria, preserva datos)
- [ ] Test de que usuario desactivado no puede usar la app
- [ ] Todos los tests pasan con mocks de Supabase

## Functional Requirements

- FR-1: Cada llamada a la API de Gemini debe registrar los tokens de input y output consumidos
- FR-2: Los costos se calculan con precios de Gemini 3 Pro Preview: Input $2.00/1M, Output $12.00/1M tokens
- FR-3: La conversion USD a COP usa TRM fijo de 4200 COP/USD
- FR-4: El limite de gasto por usuario en la demo es 1500 COP
- FR-5: Cuando un usuario alcanza el limite, todas las operaciones de IA se bloquean con mensaje descriptivo
- FR-6: El usuario bloqueado puede seguir viendo su historial y datos, pero no generar nuevas operaciones de IA
- FR-7: Al activar un usuario, se borran los registros de `token_usage` pero NO se borran `cv_history`, `skill_memory`, `base_cv` ni `interview_sessions`
- FR-8: Cada activacion/desactivacion queda registrada en `user_audit_log` con timestamp, admin, tokens y costo al momento
- FR-9: El panel de administracion es una app Streamlit separada accesible solo por admins
- FR-10: El historial de consumo se muestra al usuario en dos vistas: por CV y detallado por operacion

## Non-Goals

- Facturacion real o cobro a usuarios
- Integracion con pasarelas de pago
- Alertas por email cuando el usuario se acerca al limite
- Dashboard con graficas de uso en el tiempo (puede ser futuro)
- Tracking de tokens de modelos diferentes a Gemini
- Auto-escalado de limites

## Technical Considerations

- La API de Gemini retorna `usage_metadata` con `prompt_token_count` y `candidates_token_count` en cada respuesta
- El modelo real usado es `gemini-3-flash-preview` pero los costos se facturan como Gemini 3 Pro Preview (diferencia intencional para la demo)
- El TRM de 4200 COP/USD esta hardcodeado como constante; si se necesita actualizar, se cambia en `src/token_tracker.py`
- El `admin_app.py` corre como proceso Streamlit separado en un puerto diferente (8502)
- Para crear el primer admin: ejecutar SQL manual en Supabase Dashboard: `UPDATE user_profiles SET role = 'admin' WHERE email = 'admin@example.com'`
- Las operaciones que usan `concurrent.futures.ThreadPoolExecutor` (lineas ~1029, ~1042, ~1071, ~1085 de app.py) generan multiples llamadas; cada una debe registrarse individualmente
- El calculo de costos para validacion: `cost_cop = (input_tokens / 1_000_000 * 2.00 + output_tokens / 1_000_000 * 12.00) * 4200`

## Success Metrics

- Cada operacion de IA genera un registro en `token_usage`
- Los costos calculados coinciden con la formula definida
- Un usuario que exceda 1500 COP queda bloqueado inmediatamente
- Al reactivar un usuario, su contador vuelve a 0 pero sus datos persisten
- El admin puede ver y gestionar todos los usuarios desde el panel
- Todas las acciones de admin quedan registradas en el log de auditoria

## Open Questions

- Ninguna: todas las decisiones fueron tomadas en las preguntas de clarificacion
[/PRD]
