"""
Tests para el módulo de base de datos CVDatabase (Supabase PostgreSQL).

Todas las interacciones con Supabase se mockean para que los tests
no requieran una instancia real de base de datos.
"""

import json
import os
from unittest.mock import MagicMock, call, patch

import pytest

from src.database import CVDatabase

# ==================== Helpers ====================


class MockResponse:
    """Simula la respuesta del SDK de Supabase (postgrest.APIResponse)."""

    def __init__(self, data: list | None = None):
        self.data: list = data if data is not None else []


def _make_chain(response_data: list | None = None) -> MagicMock:
    """Crea un mock encadenable que simula queries de Supabase.

    Ejemplo: ``client.table("x").select("*").eq("id", 1).execute()``
    """
    chain = MagicMock()
    for method in (
        "select",
        "insert",
        "upsert",
        "delete",
        "eq",
        "gte",
        "is_",
        "order",
        "limit",
    ):
        getattr(chain, method).return_value = chain
    chain.execute.return_value = MockResponse(response_data)
    return chain


# ==================== Fixtures ====================


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Resetea el cliente singleton de CVDatabase entre tests."""
    CVDatabase._client = None
    yield
    CVDatabase._client = None


@pytest.fixture
def mock_client():
    """Proporciona un mock del cliente Supabase con env vars configuradas."""
    with (
        patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test-project.supabase.co",
                "SUPABASE_KEY": "test-anon-key-1234567890",
            },
        ),
        patch("src.database.create_client") as mock_create,
    ):
        client = MagicMock()
        mock_create.return_value = client
        yield client


@pytest.fixture
def cv_database(mock_client: MagicMock) -> CVDatabase:
    """Instancia de CVDatabase con cliente Supabase mockeado."""
    return CVDatabase()


@pytest.fixture
def sample_cv_data() -> dict:
    """Datos de ejemplo para un CV completo."""
    return {
        "job_title": "Senior Python Developer",
        "company": "Tech Corp",
        "language": "es",
        "theme": "classic",
        "yaml_content": ("cv:\n  name: Juan Pérez\n  email: juan@example.com\n"),
        "yaml_path": "/outputs/2024-01-01/cv.yaml",
        "pdf_path": "/outputs/2024-01-01/cv.pdf",
        "original_cv": "CV original del usuario...",
        "job_description": "Descripción de la vacante de Python Developer...",
        "gap_analysis": json.dumps(
            {
                "must_haves": ["Python", "Django", "PostgreSQL"],
                "gaps": ["Docker", "Kubernetes"],
            }
        ),
        "questions_asked": json.dumps(
            [
                "¿Tienes experiencia con Docker?",
                "¿Has trabajado con Kubernetes?",
            ]
        ),
    }


# ==================== Tests de Inicialización ====================


def test_init_creates_client():
    """Test que CVDatabase crea el cliente Supabase con las env vars."""
    with (
        patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://my-project.supabase.co",
                "SUPABASE_KEY": "my-anon-key",
            },
        ),
        patch("src.database.create_client") as mock_create,
    ):
        mock_create.return_value = MagicMock()
        CVDatabase()

        mock_create.assert_called_once_with(
            "https://my-project.supabase.co",
            "my-anon-key",
        )


def test_init_missing_env_vars():
    """Test que falla si faltan las variables de entorno."""
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("SUPABASE_URL", None)
        os.environ.pop("SUPABASE_KEY", None)
        with pytest.raises(ValueError, match="SUPABASE_URL"):
            CVDatabase()


def test_init_singleton_reuses_client():
    """Test que múltiples instancias reusan el mismo cliente."""
    with (
        patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test.supabase.co",
                "SUPABASE_KEY": "key",
            },
        ),
        patch("src.database.create_client") as mock_create,
    ):
        client = MagicMock()
        mock_create.return_value = client

        db1 = CVDatabase()
        db2 = CVDatabase()

        assert db1.client is db2.client
        mock_create.assert_called_once()


# ==================== Tests de Creación (save_cv) ====================


def test_save_cv_minimal_data(cv_database: CVDatabase, mock_client: MagicMock):
    """Test guardar CV con datos mínimos requeridos."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_id = cv_database.save_cv(
        job_title="Python Developer",
        yaml_content="cv:\n  name: Test",
    )

    assert cv_id == 1
    assert isinstance(cv_id, int)
    mock_client.table.assert_called_with("cv_history")
    chain.insert.assert_called_once()


def test_save_cv_complete_data(
    cv_database: CVDatabase,
    mock_client: MagicMock,
    sample_cv_data: dict,
):
    """Test guardar CV con todos los campos."""
    chain = _make_chain([{"id": 5, **sample_cv_data}])
    mock_client.table.return_value = chain

    cv_id = cv_database.save_cv(**sample_cv_data)

    assert cv_id == 5
    inserted = chain.insert.call_args[0][0]
    assert inserted["job_title"] == sample_cv_data["job_title"]
    assert inserted["company"] == sample_cv_data["company"]
    assert inserted["language"] == sample_cv_data["language"]
    assert inserted["theme"] == sample_cv_data["theme"]


def test_save_cv_defaults(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que se aplican valores por defecto correctamente."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_cv(job_title="Developer", yaml_content="content")

    inserted = chain.insert.call_args[0][0]
    assert inserted["language"] == "es"
    assert inserted["theme"] == "classic"


def test_save_cv_returns_incremental_ids(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que los IDs vienen de la respuesta de Supabase."""
    chain = _make_chain()
    mock_client.table.return_value = chain
    chain.execute.side_effect = [
        MockResponse([{"id": 10}]),
        MockResponse([{"id": 11}]),
    ]

    id1 = cv_database.save_cv(job_title="Job 1", yaml_content="c1")
    id2 = cv_database.save_cv(job_title="Job 2", yaml_content="c2")

    assert id1 == 10
    assert id2 == 11
    assert id2 > id1


def test_save_cv_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que user_id se incluye en los datos de insert."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain
    user_id = "550e8400-e29b-41d4-a716-446655440000"

    cv_database.save_cv(
        job_title="Dev",
        yaml_content="content",
        user_id=user_id,
    )

    inserted = chain.insert.call_args[0][0]
    assert inserted["user_id"] == user_id


def test_save_cv_without_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que user_id NO se incluye cuando es None."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_cv(job_title="Dev", yaml_content="content")

    inserted = chain.insert.call_args[0][0]
    assert "user_id" not in inserted


def test_save_cv_with_none_optional_fields(cv_database: CVDatabase, mock_client: MagicMock):
    """Test guardar CV con campos opcionales como None."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_cv(
        job_title="Dev",
        yaml_content="content",
        company=None,
        yaml_path=None,
        pdf_path=None,
        original_cv=None,
        job_description=None,
        gap_analysis=None,
        questions_asked=None,
    )

    inserted = chain.insert.call_args[0][0]
    assert inserted["company"] is None
    assert inserted["yaml_path"] is None
    assert inserted["pdf_path"] is None


def test_save_cv_with_special_characters(cv_database: CVDatabase, mock_client: MagicMock):
    """Test guardar CV con caracteres especiales (emoji, acentos, etc.)."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_cv(
        job_title="Desarrollador Senior\u2122 @ \u00d1o\u00f1o's Corp \U0001f680",
        yaml_content="cv:\n  name: Jos\u00e9 Mar\u00eda O'Brien\n  skills: ['C++', 'C#']",
        company="Caf\u00e9 & Code\u2122",
    )

    inserted = chain.insert.call_args[0][0]
    assert "\u00d1o\u00f1o" in inserted["job_title"]
    assert "Jos\u00e9 Mar\u00eda" in inserted["yaml_content"]


def test_save_cv_with_json_data(cv_database: CVDatabase, mock_client: MagicMock):
    """Test guardar gap_analysis y questions_asked como JSON strings."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    gap = json.dumps({"must_haves": ["Python", "Django"], "gaps": ["Docker"]})
    questions = json.dumps(["\u00bfTienes experiencia con Docker?", "\u00bfHas usado Kubernetes?"])

    cv_database.save_cv(
        job_title="Dev",
        yaml_content="c",
        gap_analysis=gap,
        questions_asked=questions,
    )

    inserted = chain.insert.call_args[0][0]
    parsed_gaps = json.loads(inserted["gap_analysis"])
    parsed_questions = json.loads(inserted["questions_asked"])
    assert "must_haves" in parsed_gaps
    assert len(parsed_questions) == 2


def test_save_cv_requires_job_title(cv_database: CVDatabase):
    """Test que job_title es requerido (TypeError)."""
    with pytest.raises(TypeError):
        cv_database.save_cv(yaml_content="content")  # type: ignore[call-arg]


def test_save_cv_requires_yaml_content(cv_database: CVDatabase):
    """Test que yaml_content es requerido (TypeError)."""
    with pytest.raises(TypeError):
        cv_database.save_cv(job_title="Developer")  # type: ignore[call-arg]


# ==================== Tests de Lectura (get_all_cvs) ====================


def test_get_all_cvs_empty(cv_database: CVDatabase, mock_client: MagicMock):
    """Test obtener todos los CVs cuando no hay datos."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cvs = cv_database.get_all_cvs()

    assert cvs == []
    assert isinstance(cvs, list)


def test_get_all_cvs_returns_data(cv_database: CVDatabase, mock_client: MagicMock):
    """Test obtener todos los CVs con datos (orden DESC)."""
    mock_data = [
        {
            "id": 3,
            "job_title": "Newest",
            "created_at": "2024-01-03T00:00:00+00:00",
        },
        {
            "id": 2,
            "job_title": "Middle",
            "created_at": "2024-01-02T00:00:00+00:00",
        },
        {
            "id": 1,
            "job_title": "Oldest",
            "created_at": "2024-01-01T00:00:00+00:00",
        },
    ]
    chain = _make_chain(mock_data)
    mock_client.table.return_value = chain

    cvs = cv_database.get_all_cvs()

    assert len(cvs) == 3
    assert cvs[0]["job_title"] == "Newest"
    assert cvs[-1]["job_title"] == "Oldest"


def test_get_all_cvs_calls_order_desc(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_all_cvs ordena por created_at descendente."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv_database.get_all_cvs()

    chain.order.assert_called_once_with("created_at", desc=True)


def test_get_all_cvs_selects_subset_of_fields(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_all_cvs solicita solo campos esenciales."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv_database.get_all_cvs()

    select_arg = chain.select.call_args[0][0]
    assert "id" in select_arg
    assert "job_title" in select_arg
    assert "yaml_content" not in select_arg
    assert "original_cv" not in select_arg
    assert "gap_analysis" not in select_arg


def test_get_all_cvs_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_all_cvs filtra por user_id."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv_database.get_all_cvs(user_id="user-123")

    chain.eq.assert_called_once_with("user_id", "user-123")


# ==================== Tests de Lectura (get_cv_by_id) ====================


def test_get_cv_by_id_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test obtener CV por ID cuando existe."""
    cv_data = {"id": 42, "job_title": "Dev", "yaml_content": "content"}
    chain = _make_chain([cv_data])
    mock_client.table.return_value = chain

    cv = cv_database.get_cv_by_id(42)

    assert cv is not None
    assert cv["id"] == 42
    assert cv["job_title"] == "Dev"


def test_get_cv_by_id_not_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test obtener CV por ID cuando no existe retorna None."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv = cv_database.get_cv_by_id(9999)

    assert cv is None


def test_get_cv_by_id_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_cv_by_id filtra por user_id."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.get_cv_by_id(1, user_id="user-abc")

    eq_calls = chain.eq.call_args_list
    assert call("id", 1) in eq_calls
    assert call("user_id", "user-abc") in eq_calls


def test_get_cv_by_id_returns_all_fields(
    cv_database: CVDatabase,
    mock_client: MagicMock,
    sample_cv_data: dict,
):
    """Test que get_cv_by_id retorna todos los campos."""
    full_data = {
        "id": 1,
        "created_at": "2024-01-01T00:00:00+00:00",
        "user_id": None,
        **sample_cv_data,
    }
    chain = _make_chain([full_data])
    mock_client.table.return_value = chain

    cv = cv_database.get_cv_by_id(1)

    assert cv is not None
    required_fields = [
        "id",
        "created_at",
        "job_title",
        "company",
        "language",
        "theme",
        "yaml_content",
        "yaml_path",
        "pdf_path",
        "original_cv",
        "job_description",
        "gap_analysis",
        "questions_asked",
    ]
    for field in required_fields:
        assert field in cv, f"Campo '{field}' faltante"


def test_get_cv_by_id_requires_integer(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_cv_by_id funciona con int."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv = cv_database.get_cv_by_id(1)

    assert cv is None or isinstance(cv, dict)


# ==================== Tests de Eliminación (delete_cv) ====================


def test_delete_cv_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test eliminar CV que existe retorna True."""
    chain = _make_chain([{"id": 5}])
    mock_client.table.return_value = chain

    result = cv_database.delete_cv(5)

    assert result is True
    chain.delete.assert_called_once()
    chain.eq.assert_called_with("id", 5)


def test_delete_cv_not_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test eliminar CV que no existe retorna False."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    result = cv_database.delete_cv(9999)

    assert result is False


def test_delete_cv_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que delete_cv filtra por user_id."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.delete_cv(1, user_id="user-xyz")

    eq_calls = chain.eq.call_args_list
    assert call("id", 1) in eq_calls
    assert call("user_id", "user-xyz") in eq_calls


# ==================== Tests de clear_all ====================


def test_clear_all_empty_database(cv_database: CVDatabase, mock_client: MagicMock):
    """Test limpiar base de datos vacía retorna 0."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    count = cv_database.clear_all()

    assert count == 0


def test_clear_all_with_data(cv_database: CVDatabase, mock_client: MagicMock):
    """Test limpiar base de datos con datos retorna conteo."""
    chain = _make_chain([{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}])
    mock_client.table.return_value = chain

    count = cv_database.clear_all()

    assert count == 5


def test_clear_all_returns_correct_count(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que clear_all retorna el número exacto de eliminados."""
    chain = _make_chain([{"id": 1}, {"id": 2}, {"id": 3}])
    mock_client.table.return_value = chain

    count = cv_database.clear_all()

    assert count == 3


def test_clear_all_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que clear_all filtra por user_id."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.clear_all(user_id="user-123")

    chain.eq.assert_called_once_with("user_id", "user-123")


def test_clear_all_without_user_id_uses_gte(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que clear_all sin user_id usa gte(id, 0) como filtro."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv_database.clear_all()

    chain.gte.assert_called_once_with("id", 0)


# ==================== Tests de Skill Memory ====================


def test_save_skill_answer_new(cv_database: CVDatabase, mock_client: MagicMock):
    """Test guardar nueva respuesta de skill (usage_count=1)."""
    chain = _make_chain()
    mock_client.table.return_value = chain
    chain.execute.side_effect = [
        MockResponse([]),  # select: skill no existe
        MockResponse([{"id": 1}]),  # upsert OK
    ]

    cv_database.save_skill_answer("Python", "5 a\u00f1os de experiencia")

    upsert_data = chain.upsert.call_args[0][0]
    assert upsert_data["skill_name"] == "python"
    assert upsert_data["answer_text"] == "5 a\u00f1os de experiencia"
    assert upsert_data["usage_count"] == 1


def test_save_skill_answer_update(cv_database: CVDatabase, mock_client: MagicMock):
    """Test actualizar respuesta existente (incrementa usage_count)."""
    chain = _make_chain()
    mock_client.table.return_value = chain
    chain.execute.side_effect = [
        MockResponse([{"usage_count": 3}]),  # select: existe con count=3
        MockResponse([{"id": 1}]),  # upsert
    ]

    cv_database.save_skill_answer("Docker", "Respuesta v2 mejorada")

    upsert_data = chain.upsert.call_args[0][0]
    assert upsert_data["skill_name"] == "docker"
    assert upsert_data["answer_text"] == "Respuesta v2 mejorada"
    assert upsert_data["usage_count"] == 4  # 3 + 1


def test_skill_normalization(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que las skills se normalizan a minúsculas y se limpian."""
    chain = _make_chain()
    mock_client.table.return_value = chain
    chain.execute.side_effect = [
        MockResponse([]),
        MockResponse([{"id": 1}]),
    ]

    cv_database.save_skill_answer("  React JS  ", "Frontend experience")

    upsert_data = chain.upsert.call_args[0][0]
    assert upsert_data["skill_name"] == "react js"


def test_get_skill_answer_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test recuperar respuesta de skill existente."""
    chain = _make_chain([{"answer_text": "Tengo experiencia"}])
    mock_client.table.return_value = chain

    answer = cv_database.get_skill_answer("python")

    assert answer == "Tengo experiencia"


def test_get_skill_answer_not_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test recuperar skill que no existe retorna None."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    answer = cv_database.get_skill_answer("NonExistentSkill")

    assert answer is None


def test_get_skill_answer_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_skill_answer filtra por user_id."""
    chain = _make_chain([{"answer_text": "answer"}])
    mock_client.table.return_value = chain

    cv_database.get_skill_answer("python", user_id="user-abc")

    eq_calls = chain.eq.call_args_list
    assert call("user_id", "user-abc") in eq_calls


def test_get_all_skill_answers(cv_database: CVDatabase, mock_client: MagicMock):
    """Test recuperar todas las respuestas de skills."""
    chain = _make_chain(
        [
            {"skill_name": "python", "answer_text": "5 a\u00f1os"},
            {"skill_name": "docker", "answer_text": "2 a\u00f1os"},
        ]
    )
    mock_client.table.return_value = chain

    answers = cv_database.get_all_skill_answers()

    assert answers == {"python": "5 a\u00f1os", "docker": "2 a\u00f1os"}


def test_get_all_skill_answers_empty(cv_database: CVDatabase, mock_client: MagicMock):
    """Test recuperar skills cuando no hay datos."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    answers = cv_database.get_all_skill_answers()

    assert answers == {}


def test_get_all_skill_answers_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_all_skill_answers filtra por user_id."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv_database.get_all_skill_answers(user_id="user-xyz")

    chain.eq.assert_called_once_with("user_id", "user-xyz")


def test_delete_skill_answer_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test eliminar skill que existe retorna True."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    result = cv_database.delete_skill_answer("Python")

    assert result is True
    chain.eq.assert_called_with("skill_name", "python")


def test_delete_skill_answer_not_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test eliminar skill que no existe retorna False."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    result = cv_database.delete_skill_answer("NonExistent")

    assert result is False


def test_delete_skill_answer_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que delete_skill_answer filtra por user_id."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.delete_skill_answer("python", user_id="user-abc")

    eq_calls = chain.eq.call_args_list
    assert call("user_id", "user-abc") in eq_calls


# ==================== Tests de Base CV ====================


def test_save_base_cv(cv_database: CVDatabase, mock_client: MagicMock):
    """Test guardar CV base (upsert)."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_base_cv("Mi CV base completo...")

    mock_client.table.assert_called_with("base_cv")
    chain.upsert.assert_called_once()
    upsert_data = chain.upsert.call_args[0][0]
    assert upsert_data["cv_text"] == "Mi CV base completo..."


def test_save_base_cv_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que save_base_cv incluye user_id."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_base_cv("CV text", user_id="user-abc")

    upsert_data = chain.upsert.call_args[0][0]
    assert upsert_data["user_id"] == "user-abc"


def test_save_base_cv_without_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que save_base_cv sin user_id no incluye el campo."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_base_cv("CV text")

    upsert_data = chain.upsert.call_args[0][0]
    assert "user_id" not in upsert_data


def test_save_base_cv_uses_user_id_conflict(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que save_base_cv usa on_conflict='user_id'."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_base_cv("CV text")

    _, kwargs = chain.upsert.call_args
    assert kwargs["on_conflict"] == "user_id"


def test_get_base_cv_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test recuperar CV base cuando existe."""
    chain = _make_chain([{"cv_text": "Mi CV base"}])
    mock_client.table.return_value = chain

    cv_text = cv_database.get_base_cv()

    assert cv_text == "Mi CV base"


def test_get_base_cv_not_exists(cv_database: CVDatabase, mock_client: MagicMock):
    """Test recuperar CV base cuando no existe retorna None."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv_text = cv_database.get_base_cv()

    assert cv_text is None


def test_get_base_cv_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_base_cv filtra por user_id."""
    chain = _make_chain([{"cv_text": "text"}])
    mock_client.table.return_value = chain

    cv_database.get_base_cv(user_id="user-xyz")

    chain.eq.assert_called_once_with("user_id", "user-xyz")


# ==================== Tests de Interview Sessions ====================


def test_save_interview_session(cv_database: CVDatabase, mock_client: MagicMock):
    """Test guardar sesión de entrevista."""
    chain = _make_chain([{"id": 10}])
    mock_client.table.return_value = chain

    session_id = cv_database.save_interview_session(
        cv_id=5,
        question="\u00bfCu\u00e9ntame sobre tu experiencia?",
        answer="Tengo 5 a\u00f1os...",
    )

    assert session_id == 10
    mock_client.table.assert_called_with("interview_sessions")
    inserted = chain.insert.call_args[0][0]
    assert inserted["cv_id"] == 5
    assert inserted["question"] == "\u00bfCu\u00e9ntame sobre tu experiencia?"
    assert inserted["generated_answer"] == "Tengo 5 a\u00f1os..."


def test_save_interview_session_without_cv_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test guardar sesión libre sin CV asociado."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    session_id = cv_database.save_interview_session(
        cv_id=None,
        question="Q",
        answer="A",
    )

    assert session_id == 1
    inserted = chain.insert.call_args[0][0]
    assert inserted["cv_id"] is None


def test_save_interview_session_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que save_interview_session incluye user_id."""
    chain = _make_chain([{"id": 1}])
    mock_client.table.return_value = chain

    cv_database.save_interview_session(
        cv_id=None,
        question="Q",
        answer="A",
        user_id="user-abc",
    )

    inserted = chain.insert.call_args[0][0]
    assert inserted["user_id"] == "user-abc"


def test_get_interview_sessions_all(cv_database: CVDatabase, mock_client: MagicMock):
    """Test recuperar todas las sesiones de entrevista."""
    sessions = [
        {"id": 2, "question": "Q2", "generated_answer": "A2"},
        {"id": 1, "question": "Q1", "generated_answer": "A1"},
    ]
    chain = _make_chain(sessions)
    mock_client.table.return_value = chain

    result = cv_database.get_interview_sessions()

    assert len(result) == 2
    chain.order.assert_called_once_with("created_at", desc=True)
    chain.limit.assert_called_once_with(50)


def test_get_interview_sessions_by_cv_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test filtrar sesiones por cv_id."""
    chain = _make_chain([{"id": 1, "cv_id": 5}])
    mock_client.table.return_value = chain

    cv_database.get_interview_sessions(cv_id=5)

    chain.eq.assert_any_call("cv_id", 5)


def test_get_interview_sessions_with_limit(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_interview_sessions respeta el parámetro limit."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv_database.get_interview_sessions(limit=10)

    chain.limit.assert_called_once_with(10)


def test_get_interview_sessions_with_user_id(cv_database: CVDatabase, mock_client: MagicMock):
    """Test que get_interview_sessions filtra por user_id."""
    chain = _make_chain([])
    mock_client.table.return_value = chain

    cv_database.get_interview_sessions(user_id="user-123")

    chain.eq.assert_called_once_with("user_id", "user-123")


# ==================== Tests de Múltiples Operaciones ====================


def test_multiple_saves_unique_ids(cv_database: CVDatabase, mock_client: MagicMock):
    """Test múltiples guardados retornan IDs únicos."""
    chain = _make_chain()
    mock_client.table.return_value = chain
    chain.execute.side_effect = [MockResponse([{"id": i}]) for i in range(1, 11)]

    ids = []
    for i in range(10):
        cv_id = cv_database.save_cv(
            job_title=f"Job {i}",
            yaml_content=f"content {i}",
        )
        ids.append(cv_id)

    assert len(ids) == len(set(ids))
    assert ids == list(range(1, 11))
