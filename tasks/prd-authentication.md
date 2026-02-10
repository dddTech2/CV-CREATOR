[PRD]
# PRD: Sistema de Autenticacion con Supabase Auth

## Overview

Implementar un sistema de autenticacion de usuarios en CV-App usando Supabase Auth nativo. Los usuarios deben registrarse con email y contrasena para poder usar la aplicacion. Esto protege el acceso, habilita datos per-usuario y es prerequisito para el tracking de tokens y el panel de administracion.

## Goals

- Implementar login/registro con email y contrasena usando Supabase Auth
- Proteger todas las paginas de la aplicacion tras autenticacion
- Crear un flujo de registro, login, logout y recuperacion de contrasena
- Asociar todos los datos de la aplicacion al usuario autenticado
- Preparar el sistema de roles (user/admin) para el panel de administracion

## Quality Gates

Estos comandos deben pasar para cada user story:
- `pytest tests/ -v` - Tests unitarios
- `ruff check .` - Linting
- `ruff format --check .` - Formato de codigo
- `mypy src/ --ignore-missing-imports` - Type checking

## User Stories

### US-AUTH-001: Modulo de autenticacion con Supabase Auth

**Description:** Como desarrollador, quiero crear un modulo de autenticacion reutilizable que encapsule las operaciones de Supabase Auth.

**Acceptance Criteria:**
- [ ] Crear archivo `src/auth.py` con clase `AuthManager`
- [ ] Metodo `sign_up(email: str, password: str) -> AuthResult` que registre un usuario nuevo
- [ ] Metodo `sign_in(email: str, password: str) -> AuthResult` que inicie sesion
- [ ] Metodo `sign_out() -> bool` que cierre sesion
- [ ] Metodo `get_current_user() -> User | None` que retorne el usuario actual de la sesion
- [ ] Metodo `get_user_id() -> str | None` que retorne el UUID del usuario
- [ ] Metodo `is_admin(user_id: str) -> bool` que verifique si el usuario tiene rol admin
- [ ] Crear dataclass `AuthResult` con campos: `success: bool`, `user: User | None`, `error: str | None`
- [ ] Manejar errores comunes: email duplicado, contrasena debil, credenciales invalidas
- [ ] Logging de eventos de autenticacion (sin loggear contrasenas)
- [ ] Almacenar el token de sesion en `st.session_state`

### US-AUTH-002: Tabla de perfiles de usuario en Supabase

**Description:** Como desarrollador, quiero una tabla `user_profiles` que almacene informacion adicional del usuario y su rol.

**Acceptance Criteria:**
- [ ] Crear migracion `supabase/migrations/003_user_profiles.sql`
- [ ] Tabla `user_profiles` con columnas: `id UUID PRIMARY KEY REFERENCES auth.users(id)`, `email TEXT NOT NULL`, `display_name TEXT`, `role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin'))`, `is_active BOOLEAN DEFAULT true`, `created_at TIMESTAMPTZ DEFAULT NOW()`, `updated_at TIMESTAMPTZ DEFAULT NOW()`
- [ ] Crear trigger que inserte automaticamente un perfil cuando se registra un usuario via Supabase Auth (`AFTER INSERT ON auth.users`)
- [ ] Habilitar RLS en `user_profiles`: cada usuario puede leer su propio perfil, solo admins pueden modificar `role` e `is_active`
- [ ] Crear policy para que admins puedan leer todos los perfiles
- [ ] Agregar indice en `user_profiles(role)` y `user_profiles(is_active)`

### US-AUTH-003: Pagina de Login en Streamlit

**Description:** Como usuario, quiero ver una pagina de login cuando accedo a la aplicacion para poder autenticarme.

**Acceptance Criteria:**
- [ ] Crear archivo `pages/login.py` o integrar en `app.py` como vista condicional
- [ ] Mostrar formulario con campos: Email (input tipo email), Contrasena (input tipo password)
- [ ] Boton "Iniciar Sesion" que llame a `AuthManager.sign_in()`
- [ ] Link/boton "Crear cuenta" que cambie al formulario de registro
- [ ] Mostrar errores de autenticacion de forma clara y en espanol
- [ ] Al autenticarse exitosamente, redirigir a la app principal
- [ ] Almacenar la sesion en `st.session_state` para persistir durante la sesion de Streamlit
- [ ] Diseno limpio y centrado en la pagina

### US-AUTH-004: Pagina de Registro de usuario

**Description:** Como usuario nuevo, quiero poder crear una cuenta con email y contrasena.

**Acceptance Criteria:**
- [ ] Formulario de registro con campos: Email, Contrasena, Confirmar Contrasena, Nombre (opcional)
- [ ] Validacion client-side: email valido, contrasena minimo 8 caracteres, contrasenas coinciden
- [ ] Al registrar exitosamente, mostrar mensaje de confirmacion
- [ ] Manejar error de email ya registrado con mensaje descriptivo
- [ ] Boton "Ya tengo cuenta" para volver al login
- [ ] El usuario registrado debe quedar con `role='user'` e `is_active=true` por defecto
- [ ] Logging del evento de registro (sin contrasena)

### US-AUTH-005: Proteccion de rutas y sesion

**Description:** Como desarrollador, quiero que todas las funcionalidades de la app esten protegidas tras autenticacion.

**Acceptance Criteria:**
- [ ] Crear decorador o funcion `require_auth()` que verifique si hay sesion activa en `st.session_state`
- [ ] Si no hay sesion, mostrar la pagina de login en lugar del contenido de la app
- [ ] Integrar `require_auth()` al inicio de `app.py` antes de renderizar cualquier contenido
- [ ] Agregar boton "Cerrar Sesion" en el sidebar de la aplicacion
- [ ] Al cerrar sesion, limpiar `st.session_state` y mostrar la pagina de login
- [ ] Mostrar el email del usuario logueado en el sidebar
- [ ] Si el usuario esta marcado como `is_active=false` en `user_profiles`, mostrar mensaje "Tu cuenta ha sido desactivada. Contacta al administrador." y no permitir acceso

### US-AUTH-006: Integrar user_id en todas las operaciones de base de datos

**Description:** Como desarrollador, quiero que todas las operaciones de base de datos usen el `user_id` del usuario autenticado.

**Acceptance Criteria:**
- [ ] Obtener `user_id` del `st.session_state` en cada operacion de la app
- [ ] Pasar `user_id` a todos los metodos de `CVDatabase`: `save_cv()`, `get_all_cvs()`, `get_cv_by_id()`, etc.
- [ ] El sidebar de historial solo muestra CVs del usuario actual
- [ ] La skill memory es independiente por usuario
- [ ] El CV base es independiente por usuario
- [ ] Las interview sessions son independientes por usuario
- [ ] Verificar que un usuario no puede acceder a datos de otro usuario

### US-AUTH-007: Tests de autenticacion

**Description:** Como desarrollador, quiero tests que verifiquen el flujo de autenticacion.

**Acceptance Criteria:**
- [ ] Crear archivo `tests/test_auth.py`
- [ ] Test de registro exitoso (mock Supabase Auth)
- [ ] Test de registro con email duplicado
- [ ] Test de login exitoso
- [ ] Test de login con credenciales invalidas
- [ ] Test de logout
- [ ] Test de `get_current_user()` con sesion activa y sin sesion
- [ ] Test de `is_admin()` con usuario normal y admin
- [ ] Test de proteccion de ruta con y sin sesion
- [ ] Test de usuario desactivado (`is_active=false`)
- [ ] Todos los tests pasan con `pytest tests/test_auth.py -v`

## Functional Requirements

- FR-1: Los usuarios deben registrarse con email y contrasena validos
- FR-2: Las contrasenas deben tener minimo 8 caracteres
- FR-3: La sesion debe persistir mientras el usuario no cierre sesion o cierre el navegador
- FR-4: Un usuario desactivado (`is_active=false`) no puede acceder a la aplicacion
- FR-5: El email del usuario debe mostrarse en el sidebar cuando esta logueado
- FR-6: Todos los datos (CVs, skills, entrevistas) deben estar aislados por usuario
- FR-7: Los mensajes de error deben estar en espanol
- FR-8: El sistema debe soportar dos roles: `user` y `admin`

## Non-Goals

- Login con proveedores OAuth (Google, GitHub, etc.)
- Verificacion de email (sera manual por admin activando/desactivando)
- Recuperacion de contrasena (se puede agregar despues)
- Multi-factor authentication (MFA)
- Rate limiting de intentos de login (Supabase lo maneja internamente)

## Technical Considerations

- Supabase Auth maneja internamente: hashing de contrasenas, JWTs, refresh tokens, rate limiting
- `st.session_state` es la forma estandar de manejar estado en Streamlit
- El token JWT de Supabase contiene el `user_id` que se usa en RLS
- Streamlit no tiene routing nativo; la "pagina de login" se implementa como una vista condicional en `app.py`
- Considerar usar `st.experimental_fragment` si se necesitan re-renders parciales
- El primer usuario admin se crea manualmente en Supabase Dashboard o via SQL

## Success Metrics

- Los usuarios pueden registrarse e iniciar sesion sin errores
- Los datos de cada usuario estan completamente aislados
- Un usuario desactivado no puede acceder a ninguna funcionalidad
- Todos los tests de auth pasan

## Open Questions

- Ninguna: todas las decisiones fueron tomadas en las preguntas de clarificacion
[/PRD]
