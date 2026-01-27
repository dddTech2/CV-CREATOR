"""
Tests para el módulo PDFRenderer.

Este módulo prueba todas las funcionalidades del renderizador de PDFs,
incluyendo renderizado desde archivos y strings, manejo de errores,
y limpieza de archivos temporales.
"""
import pytest
import tempfile
import os
from pathlib import Path
import shutil

from src.pdf_renderer import PDFRenderer, PDFRenderError


@pytest.fixture
def temp_output_dir():
    """
    Crea un directorio temporal para outputs de tests.

    Yields:
        Path: Directorio temporal
    """
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_yaml_content():
    """
    Provee contenido YAML válido para tests.

    Returns:
        str: Contenido YAML de ejemplo
    """
    return """cv:
  name: Test User
  email: test@example.com
  phone: "+1 234 567 8900"
  location: Test City, TC
  website: https://testuser.com
  social_networks:
    - network: LinkedIn
      username: testuser
    - network: GitHub
      username: testuser
  sections:
    Summary:
      - This is a test CV for unit testing purposes.
    Experience:
      - company: Test Company
        position: Software Engineer
        start_date: 2020-01
        end_date: 2023-12
        location: Remote
        highlights:
          - Developed testing frameworks
          - Wrote comprehensive unit tests
    Education:
      - institution: Test University
        area: Computer Science
        degree: BS
        start_date: 2016-09
        end_date: 2020-05
design:
  theme: classic
"""


@pytest.fixture
def sample_yaml_file(temp_output_dir, sample_yaml_content):
    """
    Crea un archivo YAML temporal para tests.

    Args:
        temp_output_dir: Fixture de directorio temporal
        sample_yaml_content: Fixture de contenido YAML

    Returns:
        Path: Ruta al archivo YAML temporal
    """
    yaml_file = temp_output_dir / "test_cv.yaml"
    yaml_file.write_text(sample_yaml_content, encoding="utf-8")
    return yaml_file


@pytest.fixture
def pdf_renderer(temp_output_dir):
    """
    Crea una instancia de PDFRenderer para tests.

    Args:
        temp_output_dir: Fixture de directorio temporal

    Returns:
        PDFRenderer: Instancia del renderizador
    """
    return PDFRenderer(output_dir=temp_output_dir)


# ==================== Tests de Inicialización ====================


def test_pdf_renderer_initialization(temp_output_dir):
    """Test que el renderizador se inicializa correctamente."""
    renderer = PDFRenderer(output_dir=temp_output_dir)

    assert renderer.output_dir == temp_output_dir
    assert renderer.keep_temp_files is False
    assert temp_output_dir.exists()


def test_pdf_renderer_creates_output_dir():
    """Test que el renderizador crea el directorio de salida."""
    temp_dir = Path(tempfile.mkdtemp()) / "nested" / "output"

    renderer = PDFRenderer(output_dir=temp_dir)

    assert temp_dir.exists()

    # Cleanup
    shutil.rmtree(temp_dir.parent)


def test_pdf_renderer_with_keep_temp_files():
    """Test inicialización con keep_temp_files=True."""
    temp_dir = Path(tempfile.mkdtemp())

    renderer = PDFRenderer(output_dir=temp_dir, keep_temp_files=True)

    assert renderer.keep_temp_files is True

    # Cleanup
    shutil.rmtree(temp_dir)


def test_pdf_renderer_repr(temp_output_dir):
    """Test que __repr__ retorna string informativo."""
    renderer = PDFRenderer(output_dir=temp_output_dir)

    repr_str = repr(renderer)

    assert "PDFRenderer" in repr_str
    assert str(temp_output_dir) in repr_str


# ==================== Tests de Renderizado desde String ====================


def test_render_from_string_success(pdf_renderer, sample_yaml_content):
    """Test renderizar PDF desde contenido YAML string."""
    pdf_path = pdf_renderer.render_from_string(
        sample_yaml_content, output_filename="test_cv"
    )

    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")
    assert "test_cv.pdf" in pdf_path


def test_render_from_string_auto_filename(pdf_renderer, sample_yaml_content):
    """Test que se genera filename automático si no se proporciona."""
    pdf_path = pdf_renderer.render_from_string(sample_yaml_content)

    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")
    assert "cv_" in pdf_path  # Contiene timestamp


def test_render_from_string_strips_pdf_extension(pdf_renderer, sample_yaml_content):
    """Test que se elimina extensión .pdf del filename si se proporciona."""
    pdf_path = pdf_renderer.render_from_string(
        sample_yaml_content, output_filename="test.pdf"
    )

    assert os.path.exists(pdf_path)
    # Verificar que no hay doble extensión
    assert not pdf_path.endswith(".pdf.pdf")
    assert pdf_path.endswith(".pdf")


def test_render_returns_absolute_path(pdf_renderer, sample_yaml_content):
    """Test que render() retorna ruta absoluta."""
    pdf_path = pdf_renderer.render_from_string(sample_yaml_content)

    assert Path(pdf_path).is_absolute()


# ==================== Tests de Renderizado desde Archivo ====================


def test_render_from_file_success(pdf_renderer, sample_yaml_file):
    """Test renderizar PDF desde archivo YAML."""
    pdf_path = pdf_renderer.render_from_file(sample_yaml_file)

    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")


def test_render_from_file_with_custom_output_name(pdf_renderer, sample_yaml_file):
    """Test renderizar con nombre de salida personalizado."""
    pdf_path = pdf_renderer.render_from_file(
        sample_yaml_file, output_filename="custom_name"
    )

    assert os.path.exists(pdf_path)
    assert "custom_name.pdf" in pdf_path


def test_render_from_file_not_found(pdf_renderer):
    """Test que lanza ValueError si el archivo YAML no existe."""
    with pytest.raises(ValueError, match="El archivo YAML no existe"):
        pdf_renderer.render_from_file("/nonexistent/file.yaml")


def test_render_with_yaml_path_parameter(pdf_renderer, sample_yaml_file):
    """Test usando parámetro yaml_path directamente."""
    pdf_path = pdf_renderer.render(yaml_path=sample_yaml_file)

    assert os.path.exists(pdf_path)


def test_render_with_yaml_content_parameter(pdf_renderer, sample_yaml_content):
    """Test usando parámetro yaml_content directamente."""
    pdf_path = pdf_renderer.render(yaml_content=sample_yaml_content)

    assert os.path.exists(pdf_path)


# ==================== Tests de Validación ====================


def test_render_requires_either_content_or_path(pdf_renderer):
    """Test que render() requiere yaml_content o yaml_path."""
    with pytest.raises(ValueError, match="Debe proporcionar yaml_content o yaml_path"):
        pdf_renderer.render()


def test_render_invalid_yaml_raises_error(pdf_renderer):
    """Test que YAML inválido lanza PDFRenderError."""
    invalid_yaml = "this is not valid YAML: {{{"

    with pytest.raises(PDFRenderError, match="Error al renderizar PDF"):
        pdf_renderer.render_from_string(invalid_yaml)


def test_render_incomplete_yaml_raises_error(pdf_renderer):
    """Test que YAML sin campos requeridos lanza error."""
    incomplete_yaml = """cv:
  name: ""
"""

    with pytest.raises(PDFRenderError):
        pdf_renderer.render_from_string(incomplete_yaml)


def test_validate_yaml_for_rendering_valid(pdf_renderer, sample_yaml_content):
    """Test validación de YAML válido."""
    is_valid, error = pdf_renderer.validate_yaml_for_rendering(sample_yaml_content)

    assert is_valid is True
    assert error == ""


def test_validate_yaml_for_rendering_invalid(pdf_renderer):
    """Test validación de YAML inválido."""
    invalid_yaml = "not valid yaml: {{{"

    is_valid, error = pdf_renderer.validate_yaml_for_rendering(invalid_yaml)

    assert is_valid is False
    assert len(error) > 0


# ==================== Tests de Batch Rendering ====================


def test_batch_render_success(temp_output_dir, sample_yaml_content):
    """Test renderizar múltiples archivos en batch."""
    # Crear 3 archivos YAML
    yaml_files = []
    for i in range(3):
        yaml_file = temp_output_dir / f"cv_{i}.yaml"
        yaml_file.write_text(sample_yaml_content, encoding="utf-8")
        yaml_files.append(yaml_file)

    renderer = PDFRenderer(output_dir=temp_output_dir)
    pdf_paths = renderer.batch_render(yaml_files)

    assert len(pdf_paths) == 3
    for pdf_path in pdf_paths:
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")


def test_batch_render_with_custom_output_dir(temp_output_dir, sample_yaml_content):
    """Test batch render con directorio de salida personalizado."""
    yaml_file = temp_output_dir / "cv.yaml"
    yaml_file.write_text(sample_yaml_content, encoding="utf-8")

    custom_output = temp_output_dir / "custom_output"

    renderer = PDFRenderer(output_dir=temp_output_dir)
    pdf_paths = renderer.batch_render([yaml_file], output_dir=custom_output)

    assert len(pdf_paths) == 1
    assert custom_output.exists()
    assert str(custom_output) in pdf_paths[0]


def test_batch_render_empty_list(pdf_renderer):
    """Test batch render con lista vacía."""
    pdf_paths = pdf_renderer.batch_render([])

    assert pdf_paths == []


def test_batch_render_with_errors(temp_output_dir):
    """Test que batch render reporta errores correctamente."""
    # Crear archivo válido
    valid_yaml = temp_output_dir / "valid.yaml"
    valid_yaml.write_text(
        """cv:
  name: Valid User
  email: valid@test.com
design:
  theme: classic
""",
        encoding="utf-8",
    )

    # Archivo inexistente
    invalid_file = temp_output_dir / "nonexistent.yaml"

    renderer = PDFRenderer(output_dir=temp_output_dir)

    with pytest.raises(PDFRenderError, match="Errores al renderizar"):
        renderer.batch_render([valid_yaml, invalid_file])


# ==================== Tests de Limpieza ====================


def test_cleanup_output_dir_keeps_pdfs(temp_output_dir, sample_yaml_content):
    """Test que cleanup mantiene PDFs por defecto."""
    renderer = PDFRenderer(output_dir=temp_output_dir)

    # Generar un PDF
    pdf_path = renderer.render_from_string(sample_yaml_content)

    # Crear archivo temporal
    temp_file = temp_output_dir / "temp.txt"
    temp_file.write_text("temp content")

    # Cleanup (mantener PDFs)
    count = renderer.cleanup_output_dir(keep_pdfs=True)

    assert count == 1  # Solo eliminó temp.txt
    assert os.path.exists(pdf_path)  # PDF se mantiene
    assert not temp_file.exists()  # temp.txt eliminado


def test_cleanup_output_dir_removes_all(temp_output_dir, sample_yaml_content):
    """Test que cleanup puede eliminar todo incluyendo PDFs."""
    renderer = PDFRenderer(output_dir=temp_output_dir)

    # Generar PDF
    pdf_path = renderer.render_from_string(sample_yaml_content)

    # Cleanup (eliminar todo)
    count = renderer.cleanup_output_dir(keep_pdfs=False)

    assert count == 1
    assert not os.path.exists(pdf_path)


def test_cleanup_empty_dir(pdf_renderer):
    """Test cleanup en directorio vacío."""
    count = pdf_renderer.cleanup_output_dir()

    assert count == 0


def test_cleanup_nonexistent_dir():
    """Test cleanup cuando output_dir no existe."""
    nonexistent = Path("/tmp/nonexistent_dir_12345")
    renderer = PDFRenderer(output_dir=nonexistent)

    # Eliminar el dir que se creó en __init__
    if nonexistent.exists():
        shutil.rmtree(nonexistent)

    count = renderer.cleanup_output_dir()

    assert count == 0


# ==================== Tests de Utilidades ====================


def test_get_output_dir(pdf_renderer, temp_output_dir):
    """Test obtener directorio de salida."""
    output_dir = pdf_renderer.get_output_dir()

    assert output_dir == temp_output_dir


def test_supported_themes_constant():
    """Test que SUPPORTED_THEMES está definido."""
    assert hasattr(PDFRenderer, "SUPPORTED_THEMES")
    assert isinstance(PDFRenderer.SUPPORTED_THEMES, list)
    assert len(PDFRenderer.SUPPORTED_THEMES) > 0
    assert "classic" in PDFRenderer.SUPPORTED_THEMES


# ==================== Tests de Integración ====================


def test_full_workflow_yaml_to_pdf(temp_output_dir):
    """Test flujo completo: crear YAML, validar, renderizar."""
    yaml_content = """cv:
  name: Integration Test User
  email: integration@test.com
  location: Test City
  sections:
    Summary:
      - Full integration test for PDF rendering.
design:
  theme: classic
"""

    renderer = PDFRenderer(output_dir=temp_output_dir)

    # 1. Validar YAML
    is_valid, error = renderer.validate_yaml_for_rendering(yaml_content)
    assert is_valid, f"YAML validation failed: {error}"

    # 2. Renderizar PDF
    pdf_path = renderer.render_from_string(yaml_content, output_filename="integration")

    # 3. Verificar resultado
    assert os.path.exists(pdf_path)
    assert Path(pdf_path).stat().st_size > 0  # PDF no está vacío
    assert "integration.pdf" in pdf_path


def test_render_with_special_characters(temp_output_dir):
    """Test renderizar CV con caracteres especiales."""
    yaml_content = """cv:
  name: José María Ñoño
  email: jose@example.com
  location: São Paulo, Brasil
  sections:
    Summary:
      - "Développeur avec +5 ans d'expérience"
design:
  theme: classic
"""

    renderer = PDFRenderer(output_dir=temp_output_dir)
    pdf_path = renderer.render_from_string(yaml_content)

    assert os.path.exists(pdf_path)


def test_render_different_themes(temp_output_dir):
    """Test renderizar con diferentes temas."""
    base_yaml = """cv:
  name: Theme Test User
  email: theme@test.com
design:
  theme: {}
"""

    renderer = PDFRenderer(output_dir=temp_output_dir)

    for theme in ["classic", "sb2nov"]:
        yaml_content = base_yaml.format(theme)
        pdf_path = renderer.render_from_string(
            yaml_content, output_filename=f"cv_{theme}"
        )

        assert os.path.exists(pdf_path)
        assert theme in pdf_path


# ==================== Tests de Excepciones ====================


def test_pdf_render_error_exception():
    """Test que PDFRenderError es una excepción válida."""
    error = PDFRenderError("Test error message")

    assert isinstance(error, Exception)
    assert str(error) == "Test error message"


def test_render_preserves_original_exception(pdf_renderer):
    """Test que PDFRenderError preserva la excepción original."""
    invalid_yaml = "completely invalid: }{]["

    try:
        pdf_renderer.render_from_string(invalid_yaml)
    except PDFRenderError as e:
        assert e.__cause__ is not None  # Tiene excepción original


# ==================== Tests de Edge Cases ====================


def test_render_with_pathlib_path(pdf_renderer, sample_yaml_file):
    """Test que funciona con pathlib.Path objects."""
    pdf_path = pdf_renderer.render_from_file(Path(sample_yaml_file))

    assert os.path.exists(pdf_path)


def test_render_with_string_path(pdf_renderer, sample_yaml_file):
    """Test que funciona con string paths."""
    pdf_path = pdf_renderer.render_from_file(str(sample_yaml_file))

    assert os.path.exists(pdf_path)


def test_render_with_unicode_filename(pdf_renderer, sample_yaml_content):
    """Test renderizar con filename que contiene unicode."""
    pdf_path = pdf_renderer.render_from_string(
        sample_yaml_content, output_filename="cv_josé_maría"
    )

    assert os.path.exists(pdf_path)


def test_multiple_renders_same_renderer(pdf_renderer, sample_yaml_content):
    """Test múltiples renders con la misma instancia."""
    pdf_paths = []

    for i in range(3):
        pdf_path = pdf_renderer.render_from_string(
            sample_yaml_content, output_filename=f"cv_{i}"
        )
        pdf_paths.append(pdf_path)

    assert len(pdf_paths) == 3
    assert len(set(pdf_paths)) == 3  # Todos son únicos
    for pdf_path in pdf_paths:
        assert os.path.exists(pdf_path)
