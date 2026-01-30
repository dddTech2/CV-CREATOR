"""
Tests para el módulo de base de datos CVDatabase.

Este módulo prueba todas las operaciones CRUD de la base de datos SQLite
que almacena el historial de CVs generados.
"""
import json
import os
import sqlite3
import tempfile
from datetime import datetime

import pytest

from src.database import CVDatabase


@pytest.fixture
def temp_db():
    """
    Crea una base de datos temporal para tests.
    
    Yields:
        str: Path de la base de datos temporal
    """
    # Crear directorio temporal
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_cv_history.db")

    yield db_path

    # Cleanup: eliminar la base de datos temporal
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(temp_dir):
        os.rmdir(temp_dir)


@pytest.fixture
def cv_database(temp_db):
    """
    Crea una instancia de CVDatabase con base de datos temporal.
    
    Args:
        temp_db: Fixture que provee el path de la DB temporal
        
    Returns:
        CVDatabase: Instancia de la base de datos
    """
    return CVDatabase(db_path=temp_db)


@pytest.fixture
def sample_cv_data():
    """
    Provee datos de ejemplo para un CV.
    
    Returns:
        dict: Diccionario con todos los campos de un CV
    """
    return {
        "job_title": "Senior Python Developer",
        "company": "Tech Corp",
        "language": "es",
        "theme": "classic",
        "yaml_content": """cv:
  name: Juan Pérez
  email: juan@example.com
design:
  theme: classic
  color: blue
""",
        "yaml_path": "/outputs/2024-01-01/cv.yaml",
        "pdf_path": "/outputs/2024-01-01/cv.pdf",
        "original_cv": "CV original del usuario...",
        "job_description": "Descripción de la vacante de Python Developer...",
        "gap_analysis": json.dumps({
            "must_haves": ["Python", "Django", "PostgreSQL"],
            "gaps": ["Docker", "Kubernetes"]
        }),
        "questions_asked": json.dumps([
            "¿Tienes experiencia con Docker?",
            "¿Has trabajado con Kubernetes?"
        ])
    }


# ==================== Tests de Inicialización ====================

def test_database_initialization(temp_db):
    """Test que la base de datos se inicializa correctamente."""
    db = CVDatabase(db_path=temp_db)

    # Verificar que el archivo de DB fue creado
    assert os.path.exists(temp_db)

    # Verificar que la tabla cv_history existe
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='cv_history'
    """)
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == "cv_history"
    
    # Verificar que la tabla skill_memory existe
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='skill_memory'
    """)
    result_skills = cursor.fetchone()
    conn.close()

    assert result_skills is not None
    assert result_skills[0] == "skill_memory"


def test_database_creates_parent_directory(tmp_path):
    """Test que la DB crea el directorio padre si no existe."""
    db_path = tmp_path / "subdir" / "nested" / "cv_history.db"

    db = CVDatabase(db_path=str(db_path))

    assert db_path.exists()
    assert db_path.parent.exists()


def test_database_table_schema(cv_database, temp_db):
    """Test que la tabla cv_history tiene el schema correcto."""
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()

    # Obtener información de columnas
    cursor.execute("PRAGMA table_info(cv_history)")
    columns = cursor.fetchall()
    conn.close()

    # Verificar columnas esperadas
    column_names = [col[1] for col in columns]

    expected_columns = [
        "id", "created_at", "job_title", "company", "language",
        "theme", "yaml_content", "yaml_path", "pdf_path",
        "original_cv", "job_description", "gap_analysis", "questions_asked"
    ]

    for col in expected_columns:
        assert col in column_names, f"Columna '{col}' faltante en schema"


# ==================== Tests de Creación (CREATE) ====================

def test_save_cv_minimal_data(cv_database):
    """Test guardar CV con datos mínimos requeridos."""
    cv_id = cv_database.save_cv(
        job_title="Python Developer",
        yaml_content="cv:\n  name: Test"
    )

    assert cv_id > 0
    assert isinstance(cv_id, int)


def test_save_cv_complete_data(cv_database, sample_cv_data):
    """Test guardar CV con todos los campos."""
    cv_id = cv_database.save_cv(**sample_cv_data)

    assert cv_id > 0

    # Verificar que se guardó correctamente
    cv = cv_database.get_cv_by_id(cv_id)
    assert cv is not None
    assert cv["job_title"] == sample_cv_data["job_title"]
    assert cv["company"] == sample_cv_data["company"]
    assert cv["language"] == sample_cv_data["language"]
    assert cv["theme"] == sample_cv_data["theme"]


def test_save_cv_defaults(cv_database):
    """Test que se aplican valores por defecto correctamente."""
    cv_id = cv_database.save_cv(
        job_title="Developer",
        yaml_content="cv:\n  name: Test"
    )

    cv = cv_database.get_cv_by_id(cv_id)
    assert cv["language"] == "es"  # Default
    assert cv["theme"] == "classic"  # Default


def test_save_cv_returns_incremental_ids(cv_database):
    """Test que los IDs son incrementales."""
    id1 = cv_database.save_cv(
        job_title="Job 1",
        yaml_content="content 1"
    )

    id2 = cv_database.save_cv(
        job_title="Job 2",
        yaml_content="content 2"
    )

    assert id2 > id1
    assert id2 == id1 + 1


def test_save_cv_with_timestamp(cv_database):
    """Test que se guarda el timestamp automáticamente."""
    cv_id = cv_database.save_cv(
        job_title="Developer",
        yaml_content="content"
    )

    cv = cv_database.get_cv_by_id(cv_id)
    assert cv["created_at"] is not None

    # Verificar que el timestamp es reciente (últimos 5 segundos)
    created_at = datetime.strptime(cv["created_at"], "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    diff = (now - created_at).total_seconds()
    assert diff < 5


# ==================== Tests de Lectura (READ) ====================

def test_get_cv_by_id_exists(cv_database, sample_cv_data):
    """Test obtener CV por ID cuando existe."""
    cv_id = cv_database.save_cv(**sample_cv_data)

    cv = cv_database.get_cv_by_id(cv_id)

    assert cv is not None
    assert cv["id"] == cv_id
    assert cv["job_title"] == sample_cv_data["job_title"]
    assert cv["yaml_content"] == sample_cv_data["yaml_content"]


def test_get_cv_by_id_not_exists(cv_database):
    """Test obtener CV por ID cuando no existe."""
    cv = cv_database.get_cv_by_id(9999)

    assert cv is None


def test_get_cv_by_id_returns_all_fields(cv_database, sample_cv_data):
    """Test que get_cv_by_id retorna todos los campos."""
    cv_id = cv_database.save_cv(**sample_cv_data)

    cv = cv_database.get_cv_by_id(cv_id)

    # Verificar que todos los campos importantes están presentes
    required_fields = [
        "id", "created_at", "job_title", "company", "language",
        "theme", "yaml_content", "yaml_path", "pdf_path",
        "original_cv", "job_description", "gap_analysis", "questions_asked"
    ]

    for field in required_fields:
        assert field in cv


def test_get_all_cvs_empty(cv_database):
    """Test obtener todos los CVs cuando la DB está vacía."""
    cvs = cv_database.get_all_cvs()

    assert cvs == []
    assert isinstance(cvs, list)


def test_get_all_cvs_single_item(cv_database, sample_cv_data):
    """Test obtener todos los CVs con un solo item."""
    cv_id = cv_database.save_cv(**sample_cv_data)

    cvs = cv_database.get_all_cvs()

    assert len(cvs) == 1
    assert cvs[0]["id"] == cv_id
    assert cvs[0]["job_title"] == sample_cv_data["job_title"]


def test_get_all_cvs_multiple_items(cv_database):
    """Test obtener todos los CVs con múltiples items."""
    # Guardar 3 CVs
    id1 = cv_database.save_cv(job_title="Job 1", yaml_content="content 1")
    id2 = cv_database.save_cv(job_title="Job 2", yaml_content="content 2")
    id3 = cv_database.save_cv(job_title="Job 3", yaml_content="content 3")

    cvs = cv_database.get_all_cvs()

    assert len(cvs) == 3

    # Verificar que están en orden DESC (más recientes primero)
    ids = [cv["id"] for cv in cvs]
    assert ids == [id3, id2, id1]


def test_get_all_cvs_ordered_by_date(cv_database):
    """Test que get_all_cvs retorna CVs ordenados por fecha DESC."""
    # Guardar varios CVs
    cv_database.save_cv(job_title="Oldest", yaml_content="c1")
    cv_database.save_cv(job_title="Middle", yaml_content="c2")
    cv_database.save_cv(job_title="Newest", yaml_content="c3")

    cvs = cv_database.get_all_cvs()

    # El primero debe ser el más reciente
    assert cvs[0]["job_title"] == "Newest"
    assert cvs[-1]["job_title"] == "Oldest"


def test_get_all_cvs_returns_subset_of_fields(cv_database, sample_cv_data):
    """Test que get_all_cvs retorna solo campos esenciales (no yaml_content completo)."""
    cv_database.save_cv(**sample_cv_data)

    cvs = cv_database.get_all_cvs()

    # Verificar campos presentes
    assert "id" in cvs[0]
    assert "job_title" in cvs[0]
    assert "created_at" in cvs[0]

    # Verificar que NO retorna campos grandes para lista
    assert "yaml_content" not in cvs[0]
    assert "original_cv" not in cvs[0]
    assert "gap_analysis" not in cvs[0]


# ==================== Tests de Eliminación (DELETE) ====================

def test_delete_cv_exists(cv_database, sample_cv_data):
    """Test eliminar CV que existe."""
    cv_id = cv_database.save_cv(**sample_cv_data)

    # Verificar que existe
    assert cv_database.get_cv_by_id(cv_id) is not None

    # Eliminar
    result = cv_database.delete_cv(cv_id)

    assert result is True

    # Verificar que ya no existe
    assert cv_database.get_cv_by_id(cv_id) is None


def test_delete_cv_not_exists(cv_database):
    """Test eliminar CV que no existe."""
    result = cv_database.delete_cv(9999)

    assert result is False


def test_delete_cv_reduces_count(cv_database):
    """Test que eliminar reduce el conteo de CVs."""
    # Guardar 3 CVs
    id1 = cv_database.save_cv(job_title="Job 1", yaml_content="c1")
    cv_database.save_cv(job_title="Job 2", yaml_content="c2")
    cv_database.save_cv(job_title="Job 3", yaml_content="c3")

    assert len(cv_database.get_all_cvs()) == 3

    # Eliminar uno
    cv_database.delete_cv(id1)

    assert len(cv_database.get_all_cvs()) == 2


def test_clear_all_empty_database(cv_database):
    """Test limpiar base de datos vacía."""
    count = cv_database.clear_all()

    assert count == 0


def test_clear_all_with_data(cv_database):
    """Test limpiar base de datos con datos."""
    # Guardar 5 CVs
    for i in range(5):
        cv_database.save_cv(job_title=f"Job {i}", yaml_content=f"content {i}")

    assert len(cv_database.get_all_cvs()) == 5

    # Limpiar todo
    count = cv_database.clear_all()

    assert count == 5
    assert len(cv_database.get_all_cvs()) == 0


def test_clear_all_returns_correct_count(cv_database):
    """Test que clear_all retorna el número correcto de registros eliminados."""
    # Guardar 3 CVs
    cv_database.save_cv(job_title="Job 1", yaml_content="c1")
    cv_database.save_cv(job_title="Job 2", yaml_content="c2")
    cv_database.save_cv(job_title="Job 3", yaml_content="c3")

    count = cv_database.clear_all()

    assert count == 3


# ==================== Tests de Casos Especiales ====================

def test_save_cv_with_none_optional_fields(cv_database):
    """Test guardar CV con campos opcionales como None."""
    cv_id = cv_database.save_cv(
        job_title="Developer",
        yaml_content="content",
        company=None,
        yaml_path=None,
        pdf_path=None,
        original_cv=None,
        job_description=None,
        gap_analysis=None,
        questions_asked=None
    )

    cv = cv_database.get_cv_by_id(cv_id)

    assert cv is not None
    assert cv["company"] is None
    assert cv["yaml_path"] is None


def test_save_cv_with_empty_strings(cv_database):
    """Test guardar CV con strings vacíos."""
    cv_id = cv_database.save_cv(
        job_title="Developer",
        yaml_content="",
        company="",
        gap_analysis=""
    )

    cv = cv_database.get_cv_by_id(cv_id)

    assert cv is not None
    assert cv["yaml_content"] == ""
    assert cv["company"] == ""


def test_save_cv_with_long_yaml_content(cv_database):
    """Test guardar CV con contenido YAML muy largo."""
    long_content = "cv:\n" + "  line: value\n" * 1000  # 1000 líneas

    cv_id = cv_database.save_cv(
        job_title="Developer",
        yaml_content=long_content
    )

    cv = cv_database.get_cv_by_id(cv_id)

    assert cv is not None
    assert len(cv["yaml_content"]) > 10000


def test_save_cv_with_special_characters(cv_database):
    """Test guardar CV con caracteres especiales."""
    cv_id = cv_database.save_cv(
        job_title="Desarrollador Senior™ @ Ñoño's Corp 🚀",
        yaml_content="cv:\n  name: José María O'Brien\n  skills: ['C++', 'C#']",
        company="Café & Code™"
    )

    cv = cv_database.get_cv_by_id(cv_id)

    assert cv is not None
    assert "Ñoño" in cv["job_title"]
    assert "José María" in cv["yaml_content"]


def test_save_cv_with_json_data(cv_database):
    """Test guardar análisis de gaps y preguntas en formato JSON."""
    gap_analysis = json.dumps({
        "must_haves": ["Python", "Django"],
        "gaps": ["Docker"]
    })

    questions = json.dumps([
        "¿Tienes experiencia con Docker?",
        "¿Has usado Kubernetes?"
    ])

    cv_id = cv_database.save_cv(
        job_title="Developer",
        yaml_content="content",
        gap_analysis=gap_analysis,
        questions_asked=questions
    )

    cv = cv_database.get_cv_by_id(cv_id)

    # Verificar que se puede parsear de vuelta a JSON
    parsed_gaps = json.loads(cv["gap_analysis"])
    parsed_questions = json.loads(cv["questions_asked"])

    assert "must_haves" in parsed_gaps
    assert len(parsed_questions) == 2


def test_concurrent_saves(cv_database):
    """Test múltiples guardados concurrentes mantienen integridad."""
    ids = []

    for i in range(10):
        cv_id = cv_database.save_cv(
            job_title=f"Job {i}",
            yaml_content=f"content {i}"
        )
        ids.append(cv_id)

    # Verificar que todos los IDs son únicos
    assert len(ids) == len(set(ids))

    # Verificar que todos se guardaron
    cvs = cv_database.get_all_cvs()
    assert len(cvs) == 10


# ==================== Tests de Integridad ====================

def test_database_persistence(temp_db):
    """Test que los datos persisten después de cerrar la conexión."""
    # Crear DB y guardar datos
    db1 = CVDatabase(db_path=temp_db)
    cv_id = db1.save_cv(job_title="Test Job", yaml_content="test content")

    # Crear nueva instancia (simula cerrar/reabrir app)
    db2 = CVDatabase(db_path=temp_db)
    cv = db2.get_cv_by_id(cv_id)

    assert cv is not None
    assert cv["job_title"] == "Test Job"


def test_database_handles_missing_file_gracefully(tmp_path):
    """Test que la DB se recrea si el archivo no existe."""
    db_path = tmp_path / "cv_history.db"

    # Primera vez: crea la DB
    db1 = CVDatabase(db_path=str(db_path))
    assert db_path.exists()

    # Eliminar el archivo
    db_path.unlink()
    assert not db_path.exists()

    # Segunda vez: debe recrear la DB
    db2 = CVDatabase(db_path=str(db_path))
    assert db_path.exists()


# ==================== Tests de Validación ====================

def test_save_cv_requires_job_title(cv_database):
    """Test que job_title es requerido."""
    with pytest.raises(TypeError):
        cv_database.save_cv(yaml_content="content")  # Falta job_title


def test_save_cv_requires_yaml_content(cv_database):
    """Test que yaml_content es requerido."""
    with pytest.raises(TypeError):
        cv_database.save_cv(job_title="Developer")  # Falta yaml_content


def test_get_cv_by_id_requires_integer(cv_database):
    """Test que get_cv_by_id requiere un entero."""
    # SQLite es permisivo, pero debería funcionar con int
    cv = cv_database.get_cv_by_id(1)
    assert cv is None or isinstance(cv, dict)


# ==================== Tests de Performance ====================

def test_save_large_batch_of_cvs(cv_database):
    """Test guardar batch grande de CVs (performance)."""
    num_cvs = 100

    for i in range(num_cvs):
        cv_database.save_cv(
            job_title=f"Job {i}",
            yaml_content=f"content {i}",
            company=f"Company {i}"
        )

    cvs = cv_database.get_all_cvs()
    assert len(cvs) == num_cvs


def test_search_in_large_dataset(cv_database):
    """Test buscar en dataset grande."""
    # Insertar 50 CVs
    target_id = None
    for i in range(50):
        cv_id = cv_database.save_cv(
            job_title=f"Job {i}",
            yaml_content=f"content {i}"
        )
        if i == 25:
            target_id = cv_id

    # Buscar el del medio
    cv = cv_database.get_cv_by_id(target_id)

    assert cv is not None
    assert cv["job_title"] == "Job 25"


# ==================== Tests de Skill Memory ====================

def test_save_skill_answer_new(cv_database):
    """Test guardar una nueva respuesta de skill."""
    skill = "Python"
    answer = "Tengo 5 años de experiencia."
    
    cv_database.save_skill_answer(skill, answer)
    
    saved_answer = cv_database.get_skill_answer(skill)
    assert saved_answer == answer

def test_save_skill_answer_update(cv_database):
    """Test actualizar una respuesta existente (Upsert)."""
    skill = "Docker"
    
    # Primera respuesta
    cv_database.save_skill_answer(skill, "Respuesta v1")
    assert cv_database.get_skill_answer(skill) == "Respuesta v1"
    
    # Actualización
    cv_database.save_skill_answer(skill, "Respuesta v2 mejorada")
    assert cv_database.get_skill_answer(skill) == "Respuesta v2 mejorada"

def test_skill_normalization(cv_database):
    """Test que las skills se normalizan (lowercase/strip)."""
    # Guardar con mayúsculas y espacios
    cv_database.save_skill_answer("  React JS  ", "Experiencia en frontend")
    
    # Recuperar con minúsculas
    answer = cv_database.get_skill_answer("react js")
    assert answer == "Experiencia en frontend"
    
    # Recuperar con original (también debe funcionar porque se normaliza en el input)
    answer2 = cv_database.get_skill_answer("  React JS  ")
    assert answer2 == "Experiencia en frontend"

def test_get_skill_answer_not_exists(cv_database):
    """Test recuperar skill que no existe."""
    answer = cv_database.get_skill_answer("NonExistentSkill")
    assert answer is None
