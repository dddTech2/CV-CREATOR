# US-011: Backend - Base de datos para historial

## 📋 Resumen

**User Story:** Como sistema, necesito una base de datos SQLite para almacenar historial de CVs generados.

**Estado:** ✅ COMPLETADA

**Fecha:** 25 de enero de 2026

---

## 🎯 Objetivos Completados

✅ Archivo `src/database.py` con clase `CVDatabase`  
✅ Tabla `cv_history` con todos los campos requeridos  
✅ Métodos CRUD completos (create, read, list, delete)  
✅ Inicialización automática de DB en primera ejecución  
✅ Suite completa de 35 tests unitarios  
✅ 100% de tests pasando  

---

## 📊 Métricas

- **Código de producción:** 178 líneas (`src/database.py`)
- **Código de tests:** 599 líneas (`tests/test_database.py`)
- **Total:** 777 líneas
- **Tests:** 35 tests unitarios (100% passing ✅)
- **Cobertura estimada:** ~95%

---

## 🏗️ Arquitectura

### Clase Principal: `CVDatabase`

```python
class CVDatabase:
    """Gestor de base de datos SQLite para el historial de CVs generados."""
    
    def __init__(self, db_path: str = "data/cv_history.db"):
        """Inicializa la base de datos y crea la tabla si no existe."""
        
    def save_cv(
        self,
        job_title: str,
        yaml_content: str,
        company: Optional[str] = None,
        language: str = "es",
        theme: str = "classic",
        yaml_path: Optional[str] = None,
        pdf_path: Optional[str] = None,
        original_cv: Optional[str] = None,
        job_description: Optional[str] = None,
        gap_analysis: Optional[str] = None,
        questions_asked: Optional[str] = None
    ) -> int:
        """Guarda un CV generado y retorna su ID."""
        
    def get_all_cvs(self) -> List[Dict]:
        """Obtiene todos los CVs ordenados por fecha (más recientes primero)."""
        
    def get_cv_by_id(self, cv_id: int) -> Optional[Dict]:
        """Obtiene un CV específico por su ID."""
        
    def delete_cv(self, cv_id: int) -> bool:
        """Elimina un CV del historial."""
        
    def clear_all(self) -> int:
        """Elimina todos los CVs del historial."""
```

---

## 🗄️ Schema de Base de Datos

### Tabla: `cv_history`

```sql
CREATE TABLE IF NOT EXISTS cv_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    job_title TEXT NOT NULL,
    company TEXT,
    language TEXT DEFAULT 'es',
    theme TEXT DEFAULT 'classic',
    yaml_content TEXT NOT NULL,
    yaml_path TEXT,
    pdf_path TEXT,
    original_cv TEXT,
    job_description TEXT,
    gap_analysis TEXT,
    questions_asked TEXT
)
```

### Campos:

| Campo | Tipo | Obligatorio | Default | Descripción |
|-------|------|-------------|---------|-------------|
| `id` | INTEGER | Sí (PK) | AUTOINCREMENT | Identificador único |
| `created_at` | TIMESTAMP | Sí | CURRENT_TIMESTAMP | Fecha de creación |
| `job_title` | TEXT | Sí | - | Título de la vacante |
| `company` | TEXT | No | NULL | Nombre de la empresa |
| `language` | TEXT | No | 'es' | Idioma del CV (es, en, pt, fr) |
| `theme` | TEXT | No | 'classic' | Tema de RenderCV usado |
| `yaml_content` | TEXT | Sí | - | Contenido YAML completo |
| `yaml_path` | TEXT | No | NULL | Ruta del archivo YAML guardado |
| `pdf_path` | TEXT | No | NULL | Ruta del PDF generado |
| `original_cv` | TEXT | No | NULL | CV original del usuario |
| `job_description` | TEXT | No | NULL | Descripción de la vacante |
| `gap_analysis` | TEXT | No | NULL | Resultado del análisis de brechas (JSON) |
| `questions_asked` | TEXT | No | NULL | Preguntas hechas al usuario (JSON) |

---

## 💡 Características Implementadas

### 1. Inicialización Automática

La base de datos y la tabla se crean automáticamente en la primera ejecución:

```python
db = CVDatabase()  # Crea data/cv_history.db si no existe
```

También crea el directorio padre si no existe:

```python
db = CVDatabase(db_path="custom/path/to/cv_history.db")
# Crea el directorio "custom/path/to/" automáticamente
```

### 2. Operaciones CRUD Completas

#### CREATE: Guardar CV

```python
cv_id = db.save_cv(
    job_title="Senior Python Developer",
    yaml_content=yaml_str,
    company="Tech Corp",
    language="es",
    theme="classic",
    yaml_path="/outputs/2024-01-01/cv.yaml",
    pdf_path="/outputs/2024-01-01/cv.pdf",
    gap_analysis=json.dumps({"gaps": ["Docker"]})
)
print(f"CV guardado con ID: {cv_id}")
```

#### READ: Obtener CV por ID

```python
cv = db.get_cv_by_id(cv_id)
if cv:
    print(f"CV: {cv['job_title']}")
    print(f"Creado: {cv['created_at']}")
    print(f"YAML: {cv['yaml_content']}")
```

#### LIST: Listar todos los CVs

```python
cvs = db.get_all_cvs()
for cv in cvs:
    print(f"{cv['id']}: {cv['job_title']} ({cv['created_at']})")
```

**Nota:** `get_all_cvs()` retorna solo campos esenciales para listar (no incluye `yaml_content`, `original_cv`, etc. para optimizar memoria).

#### DELETE: Eliminar CV

```python
success = db.delete_cv(cv_id)
if success:
    print("CV eliminado correctamente")
else:
    print("CV no encontrado")
```

#### CLEAR: Limpiar toda la base de datos

```python
count = db.clear_all()
print(f"Eliminados {count} CVs")
```

### 3. Ordenamiento Inteligente

Los CVs se retornan ordenados por fecha de creación descendente (más recientes primero), con desempate por ID:

```sql
ORDER BY created_at DESC, id DESC
```

Esto garantiza que incluso si múltiples CVs se crean en el mismo segundo, se mantiene el orden correcto.

### 4. Soporte para JSON

Los campos `gap_analysis` y `questions_asked` pueden almacenar estructuras JSON:

```python
import json

gap_analysis = json.dumps({
    "must_haves": ["Python", "Django", "PostgreSQL"],
    "gaps": ["Docker", "Kubernetes"]
})

questions = json.dumps([
    "¿Tienes experiencia con Docker?",
    "¿Has trabajado con Kubernetes?"
])

cv_id = db.save_cv(
    job_title="Developer",
    yaml_content="...",
    gap_analysis=gap_analysis,
    questions_asked=questions
)

# Recuperar y parsear JSON
cv = db.get_cv_by_id(cv_id)
gaps = json.loads(cv["gap_analysis"])
questions_list = json.loads(cv["questions_asked"])
```

### 5. Persistencia y Durabilidad

Los datos persisten entre sesiones. La base de datos sobrevive al cierre y reapertura de la aplicación:

```python
# Sesión 1
db1 = CVDatabase()
cv_id = db1.save_cv(job_title="Test", yaml_content="test")

# Sesión 2 (después de reiniciar la app)
db2 = CVDatabase()
cv = db2.get_cv_by_id(cv_id)
assert cv is not None  # ✅ Datos persisten
```

---

## 🧪 Cobertura de Tests

### Categorías de Tests (35 total)

#### Inicialización (3 tests)
- ✅ Creación de base de datos
- ✅ Creación de directorios padre
- ✅ Validación del schema de tabla

#### Operaciones CREATE (8 tests)
- ✅ Guardar con datos mínimos
- ✅ Guardar con datos completos
- ✅ Aplicación de defaults
- ✅ IDs incrementales
- ✅ Timestamps automáticos

#### Operaciones READ (8 tests)
- ✅ Obtener por ID (existe/no existe)
- ✅ Listar CVs (vacío/uno/múltiples)
- ✅ Ordenamiento por fecha
- ✅ Subset de campos en lista

#### Operaciones DELETE (5 tests)
- ✅ Eliminar CV existente/no existente
- ✅ Reducción de conteo
- ✅ Limpiar toda la base de datos

#### Casos Especiales (7 tests)
- ✅ Campos opcionales como None
- ✅ Strings vacíos
- ✅ Contenido YAML muy largo (>10KB)
- ✅ Caracteres especiales (ñ, ™, emojis 🚀)
- ✅ Almacenamiento de JSON
- ✅ Múltiples guardados concurrentes

#### Integridad (2 tests)
- ✅ Persistencia entre sesiones
- ✅ Recreación de archivo si se elimina

#### Performance (2 tests)
- ✅ Batch de 100 CVs
- ✅ Búsqueda en dataset grande (50 items)

---

## 🔌 Integración con Otros Módulos

### Flujo Completo de Generación de CV

```python
from src.cv_parser import CVParser
from src.yaml_generator import YAMLGenerator, ContactInfo
from src.yaml_validator import YAMLValidator
from src.database import CVDatabase

# 1. Parsear CV del usuario
parser = CVParser()
cv_data = parser.parse_text(cv_text)

# 2. Generar YAML
generator = YAMLGenerator()
yaml_content = generator.generate(
    cv_data=cv_data,
    contact_info=ContactInfo(name="Juan Pérez"),
    theme="classic",
    language="es"
)

# 3. Validar YAML
validator = YAMLValidator()
result = validator.validate(yaml_content)
if not result.is_valid:
    raise ValueError(result.get_summary())

# 4. Guardar en base de datos
db = CVDatabase()
cv_id = db.save_cv(
    job_title="Senior Python Developer",
    company="Tech Corp",
    yaml_content=yaml_content,
    language="es",
    theme="classic",
    original_cv=cv_text,
    job_description=job_desc
)

print(f"✅ CV guardado con ID: {cv_id}")

# 5. Listar historial
cvs = db.get_all_cvs()
for cv in cvs:
    print(f"- {cv['job_title']} @ {cv['company']} ({cv['created_at']})")
```

---

## 📂 Estructura de Archivos

```
cv-app/
├── src/
│   └── database.py           # ✅ 178 líneas
├── tests/
│   └── test_database.py      # ✅ 599 líneas
├── data/
│   └── cv_history.db         # Creado automáticamente
└── docs/
    └── US-011-RESUMEN.md     # Este documento
```

---

## 🚀 Uso en la Aplicación Streamlit (US-017)

### Sidebar con Historial

```python
import streamlit as st
from src.database import CVDatabase

db = CVDatabase()

# Mostrar historial en sidebar
st.sidebar.header("📚 Historial de CVs")

cvs = db.get_all_cvs()
st.sidebar.write(f"Total: {len(cvs)} CVs generados")

for cv in cvs:
    with st.sidebar.expander(f"{cv['job_title']} - {cv['created_at'][:10]}"):
        st.write(f"**Empresa:** {cv['company'] or 'N/A'}")
        st.write(f"**Idioma:** {cv['language'].upper()}")
        st.write(f"**Tema:** {cv['theme']}")
        
        if st.button(f"Cargar CV #{cv['id']}", key=f"load_{cv['id']}"):
            full_cv = db.get_cv_by_id(cv['id'])
            st.session_state.loaded_cv = full_cv
            
        if st.button(f"Eliminar", key=f"delete_{cv['id']}"):
            db.delete_cv(cv['id'])
            st.rerun()

# Botón para limpiar todo
if st.sidebar.button("🗑️ Limpiar todo"):
    db.clear_all()
    st.rerun()
```

---

## 🔍 Decisiones de Diseño

### ¿Por qué SQLite en lugar de SQLAlchemy ORM?

**Decisión:** Usar `sqlite3` directo en lugar de SQLAlchemy.

**Razones:**
1. **Simplicidad:** La aplicación es single-user local, no necesita migración de schemas complejos
2. **Rendimiento:** SQLite directo es más rápido para operaciones simples
3. **Dependencias:** Menos dependencias = menos surface area para bugs
4. **Transparencia:** El SQL es explícito y fácil de debuggear

**Trade-off aceptado:** Si en el futuro necesitamos PostgreSQL o MySQL, tendríamos que refactorizar. Pero no está en el scope del PRD.

### ¿Por qué `get_all_cvs()` no retorna `yaml_content`?

**Decisión:** Retornar solo campos esenciales en la lista.

**Razones:**
1. **Performance:** Un YAML puede tener >10KB. Retornar 100 CVs completos = >1MB en memoria
2. **UX:** El sidebar de Streamlit solo necesita metadatos (título, fecha, tema)
3. **Lazy loading:** Solo cargar el contenido completo cuando el usuario hace click

**Implementación:**
```python
# Lista rápida (solo metadatos)
cvs = db.get_all_cvs()  # Retorna: id, created_at, job_title, company, etc.

# Cargar completo solo cuando se necesita
full_cv = db.get_cv_by_id(cv['id'])  # Retorna TODO incluyendo yaml_content
```

### ¿Por qué ordenar por `created_at DESC, id DESC`?

**Decisión:** Ordenamiento doble para desempate.

**Problema:** SQLite guarda timestamps con resolución de segundos. Si guardas 2 CVs en el mismo segundo, el orden era indeterminado.

**Solución:** Usar ID como criterio de desempate:
```sql
ORDER BY created_at DESC, id DESC
```

Esto garantiza orden consistente incluso con timestamps idénticos.

---

## ✅ Acceptance Criteria Cumplidos

| Criterio | Estado | Evidencia |
|----------|--------|-----------|
| Archivo `src/database.py` con modelos | ✅ | `src/database.py` existe |
| Tabla `cv_history` con campos especificados | ✅ | Test `test_database_table_schema` pasa |
| Métodos CRUD: create, read, list, delete | ✅ | `save_cv()`, `get_cv_by_id()`, `get_all_cvs()`, `delete_cv()` implementados |
| Inicialización automática de DB | ✅ | Test `test_database_initialization` pasa |
| Tests de operaciones de base de datos | ✅ | 35 tests (100% passing) |

---

## 📚 Referencias

- **PRD.md:** Líneas 137-145 (especificación de US-011)
- **Código fuente:** `src/database.py`
- **Tests:** `tests/test_database.py`
- **Schema JSON:** SQLite no usa schema JSON (usa SQL directo)

---

## 🎓 Lecciones Aprendidas

1. **Timestamps con resolución de segundos requieren desempate:** Agregar `ORDER BY id DESC` como criterio secundario.

2. **Separar metadatos de contenido:** `get_all_cvs()` retorna lista ligera, `get_cv_by_id()` retorna objeto completo.

3. **Crear directorios padre automáticamente:** Mejora UX y previene errores de "FileNotFoundError".

4. **Tests de persistencia son críticos:** Verificar que los datos sobreviven al cierre/apertura de la app.

5. **Soporte para JSON en campos TEXT:** Permite flexibilidad sin complicar el schema.

---

## 🔜 Próximos Pasos

- ✅ **US-011 completada**
- ⏭️ **US-010:** Implementar `PDFRenderer` para renderizar YAML → PDF
- ⏭️ **US-012:** Crear frontend Streamlit con tabs
- ⏭️ **US-017:** Integrar el historial en sidebar de Streamlit

---

## 📊 Resumen Ejecutivo

**US-011 fue completada exitosamente** con:

- ✅ 178 líneas de código de producción
- ✅ 599 líneas de tests (35 tests)
- ✅ 100% de tests pasando
- ✅ Schema SQL completamente documentado
- ✅ Integración lista para uso en frontend Streamlit

La base de datos SQLite provee una solución simple, robusta y eficiente para almacenar el historial de CVs generados, cumpliendo todos los requisitos funcionales y no funcionales del PRD.

---

**Implementado por:** OpenCode Assistant  
**Fecha de completitud:** 25 de enero de 2026  
**Versión:** 1.0  
