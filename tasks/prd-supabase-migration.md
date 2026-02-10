[PRD]
# PRD: Migracion de SQLite a Supabase PostgreSQL

## Overview

Migrar la capa de persistencia de la aplicacion CV-App desde SQLite local (`src/database.py`) hacia Supabase PostgreSQL como unica base de datos. Esto elimina la dependencia de archivos locales, habilita multiusuario y prepara la infraestructura para autenticacion y tracking de tokens.

## Goals

- Reemplazar completamente SQLite por Supabase PostgreSQL
- Mantener todas las funcionalidades actuales de la clase `CVDatabase` sin regresiones
- Crear el esquema PostgreSQL equivalente a las 4 tablas actuales (`cv_history`, `skill_memory`, `base_cv`, `interview_sessions`)
- Configurar la conexion a Supabase via variables de entorno (`SUPABASE_URL`, `SUPABASE_KEY`)
- Mantener la misma interfaz publica de `CVDatabase` para minimizar cambios en `app.py`

## Quality Gates

Estos comandos deben pasar para cada user story:
- `pytest tests/ -v` - Tests unitarios
- `ruff check .` - Linting
- `ruff format --check .` - Formato de codigo
- `mypy src/ --ignore-missing-imports` - Type checking

## User Stories

### US-DB-001: Configuracion del proyecto Supabase y esquema SQL

**Description:** Como desarrollador, quiero tener el esquema SQL de PostgreSQL definido y documentado para que pueda crear las tablas en Supabase.

**Acceptance Criteria:**
- [ ] Crear archivo `supabase/migrations/001_initial_schema.sql` con las 4 tablas migradas a PostgreSQL
- [ ] Tabla `cv_history`: reemplazar `INTEGER PRIMARY KEY AUTOINCREMENT` por `SERIAL PRIMARY KEY`, `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` por `TIMESTAMPTZ DEFAULT NOW()`
- [ ] Tabla `skill_memory`: `skill_name TEXT PRIMARY KEY` se mantiene, `ON CONFLICT` se convierte a sintaxis PostgreSQL con `ON CONFLICT DO UPDATE`
- [ ] Tabla `base_cv`: mantener constraint `CHECK (id = 1)` para singleton
- [ ] Tabla `interview_sessions`: mantener `FOREIGN KEY` con `ON DELETE CASCADE`
- [ ] Agregar columna `user_id UUID REFERENCES auth.users(id)` a las tablas `cv_history`, `skill_memory`, `base_cv` e `interview_sessions` (preparacion para auth)
- [ ] Crear indices en `cv_history(user_id, created_at)` y `skill_memory(user_id)`
- [ ] Documentar el esquema en un comentario SQL al inicio del archivo

### US-DB-002: Instalacion de dependencias y configuracion de conexion

**Description:** Como desarrollador, quiero configurar la conexion a Supabase en el proyecto para poder interactuar con la base de datos.

**Acceptance Criteria:**
- [ ] Agregar `supabase` (Python SDK) a `requirements.txt`
- [ ] Crear variables de entorno `SUPABASE_URL` y `SUPABASE_KEY` en `.env.example`
- [ ] Agregar `SUPABASE_URL` y `SUPABASE_KEY` a `.env` (con placeholders)
- [ ] Verificar que `streamlit_app` puede leer las variables de entorno correctamente
- [ ] Agregar `supabase` a la seccion de imports en `src/database.py`

### US-DB-003: Reescribir clase CVDatabase para Supabase

**Description:** Como desarrollador, quiero reescribir `src/database.py` reemplazando sqlite3 por el SDK de Supabase, manteniendo la misma interfaz publica.

**Acceptance Criteria:**
- [ ] Reescribir `__init__` para inicializar el cliente Supabase en lugar de sqlite3
- [ ] Reescribir `save_cv()` usando `supabase.table('cv_history').insert()`
- [ ] Reescribir `get_all_cvs()` usando `supabase.table('cv_history').select().order()`
- [ ] Reescribir `get_cv_by_id()` usando `supabase.table('cv_history').select().eq()`
- [ ] Reescribir `delete_cv()` usando `supabase.table('cv_history').delete().eq()`
- [ ] Reescribir `clear_all()` usando `supabase.table('cv_history').delete()`
- [ ] Reescribir `save_skill_answer()` con upsert de PostgreSQL
- [ ] Reescribir `get_skill_answer()` y `get_all_skill_answers()`
- [ ] Reescribir `delete_skill_answer()`
- [ ] Reescribir `save_base_cv()` y `get_base_cv()` manteniendo logica singleton
- [ ] Reescribir `save_interview_session()` y `get_interview_sessions()`
- [ ] Todos los metodos deben aceptar un parametro opcional `user_id: str | None = None`
- [ ] Mantener el logging existente con `src.logger`
- [ ] Manejar excepciones de Supabase y convertirlas en errores descriptivos

### US-DB-004: Row Level Security (RLS) en Supabase

**Description:** Como desarrollador, quiero configurar RLS para que cada usuario solo pueda ver y modificar sus propios datos.

**Acceptance Criteria:**
- [ ] Crear archivo `supabase/migrations/002_rls_policies.sql`
- [ ] Habilitar RLS en las 4 tablas: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`
- [ ] Crear policy SELECT: `auth.uid() = user_id` para cada tabla
- [ ] Crear policy INSERT: `auth.uid() = user_id` para cada tabla
- [ ] Crear policy UPDATE: `auth.uid() = user_id` para cada tabla
- [ ] Crear policy DELETE: `auth.uid() = user_id` para cada tabla
- [ ] Crear policy especial para admins que puedan ver todos los registros (usar claim `is_admin` en JWT)
- [ ] Documentar las policies con comentarios SQL

### US-DB-005: Actualizar tests para Supabase

**Description:** Como desarrollador, quiero que los tests existentes sigan pasando con la nueva capa de base de datos.

**Acceptance Criteria:**
- [ ] Actualizar `tests/test_database.py` para mockear el cliente Supabase
- [ ] Crear fixture `mock_supabase_client` que simule las respuestas de Supabase
- [ ] Todos los tests existentes de base de datos deben pasar con los mocks
- [ ] Agregar tests para el parametro `user_id` en cada metodo
- [ ] Agregar test para verificar que RLS se aplica (mock de politicas)
- [ ] Verificar que `pytest tests/ -v` pasa al 100%

### US-DB-006: Actualizar app.py para usar nueva base de datos

**Description:** Como desarrollador, quiero actualizar `app.py` para que use la nueva version de `CVDatabase` con Supabase.

**Acceptance Criteria:**
- [ ] Actualizar la instanciacion de `CVDatabase()` en `app.py` (ya no necesita `db_path`)
- [ ] Pasar `user_id` a todos los metodos de la base de datos donde se tenga sesion de usuario
- [ ] Verificar que el sidebar de historial sigue funcionando con datos de Supabase
- [ ] Verificar que guardar/cargar/eliminar CVs funciona correctamente
- [ ] Verificar que skill memory funciona correctamente
- [ ] Verificar que interview sessions funciona correctamente
- [ ] Eliminar archivo `data/cv_history.db` del proyecto y de `.gitignore` si aplica

## Functional Requirements

- FR-1: La aplicacion debe conectarse a Supabase PostgreSQL usando las variables de entorno `SUPABASE_URL` y `SUPABASE_KEY`
- FR-2: Todas las operaciones CRUD existentes deben funcionar identicamente con Supabase
- FR-3: Cada registro debe asociarse a un `user_id` para soporte multiusuario
- FR-4: Las politicas RLS deben impedir que un usuario vea datos de otro usuario
- FR-5: Los errores de conexion a Supabase deben manejarse gracefully mostrando un mensaje en Streamlit
- FR-6: La aplicacion no debe tener ninguna referencia a sqlite3 al finalizar la migracion

## Non-Goals

- Migracion de datos existentes de SQLite a Supabase (no hay datos en produccion)
- Implementacion de autenticacion (sera PRD separado)
- Tracking de tokens (sera PRD separado)
- Soporte offline o fallback a SQLite
- Uso de ORMs como SQLAlchemy

## Technical Considerations

- La app corre en Streamlit Cloud, que ya soporta secrets/env vars
- El SDK de Supabase para Python es `supabase-py` (`pip install supabase`)
- La columna `user_id` se agrega desde el inicio para evitar migraciones futuras
- Considerar connection pooling si se necesita en el futuro (Supabase lo maneja internamente)
- El singleton de `base_cv` necesita adaptarse por usuario: cambiar constraint `CHECK (id = 1)` a `UNIQUE(user_id)` para que cada usuario tenga un solo CV base

## Success Metrics

- 0 referencias a sqlite3 en el codigo fuente
- Todos los tests existentes pasan con mocks de Supabase
- La aplicacion funciona correctamente conectada a una instancia de Supabase
- Las 4 tablas tienen RLS habilitado y policies configuradas

## Open Questions

- Ninguna: todas las decisiones fueron tomadas en las preguntas de clarificacion
[/PRD]
