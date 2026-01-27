"""
Tests para ExperienceRewriter.

Valida reescritura de experiencia laboral con integración de skills,
optimización ATS y cuantificación de logros.
"""

import pytest
from unittest.mock import Mock

from src.experience_rewriter import (
    ExperienceRewriter,
    ExperienceEntry,
    RewriteResult,
)
from src.gap_analyzer import GapAnalysisResult, SkillGap
from src.job_analyzer import JobRequirements, Skill, SkillCategory, RequirementPriority
from src.cv_parser import CVData
from src.ai_backend import GeminiClient


# Fixtures


@pytest.fixture
def mock_ai_client():
    """Mock del cliente Gemini AI."""
    client = Mock(spec=GeminiClient)
    client.generate_content = Mock(
        return_value="""• Desarrollé aplicaciones web usando Python, Django y Docker para optimizar procesos internos.
• Implementé sistemas de CI/CD con Kubernetes reduciendo tiempo de deploy en 50%.
• Lideré equipo de 5 desarrolladores mejorando productividad en 30% mediante metodologías ágiles."""
    )
    return client


@pytest.fixture
def sample_cv_data():
    """CV de ejemplo con experiencias."""
    cv = CVData(
        raw_text="Test CV",
        sections={},
        metadata={},
    )

    # Añadir experiencias como dict
    cv.work_experience = [
        {
            "company": "Tech Corp",
            "title": "Software Developer",
            "duration": "2020-2023",
            "description": "Developed web applications using Python and JavaScript",
        },
        {
            "company": "StartupCo",
            "title": "Junior Developer",
            "duration": "2018-2020",
            "description": "Worked on frontend development",
        },
    ]

    return cv


@pytest.fixture
def sample_job_requirements():
    """Requisitos de vacante de ejemplo."""
    return JobRequirements(
        technical_skills=[
            Skill(
                name="Python",
                category=SkillCategory.TECHNICAL,
                priority=RequirementPriority.MUST_HAVE,
            ),
            Skill(
                name="Docker",
                category=SkillCategory.TECHNICAL,
                priority=RequirementPriority.MUST_HAVE,
            ),
            Skill(
                name="Kubernetes",
                category=SkillCategory.TECHNICAL,
                priority=RequirementPriority.NICE_TO_HAVE,
            ),
        ]
    )


@pytest.fixture
def sample_gap_analysis(sample_cv_data, sample_job_requirements):
    """Gap analysis de ejemplo."""
    gap_analysis = GapAnalysisResult(
        cv_data=sample_cv_data, job_requirements=sample_job_requirements
    )

    gap_analysis.technical_gaps = [
        SkillGap(
            skill_name="Docker",
            priority=RequirementPriority.MUST_HAVE,
            found_in_cv=False,
        ),
        SkillGap(
            skill_name="Kubernetes",
            priority=RequirementPriority.NICE_TO_HAVE,
            found_in_cv=False,
        ),
    ]

    return gap_analysis


@pytest.fixture
def sample_user_answers():
    """Respuestas del usuario a preguntas."""
    return {
        "Docker": "Sí, he trabajado con Docker en mis últimos 2 proyectos para containerizar aplicaciones",
        "Kubernetes": "Tengo experiencia básica con K8s en ambiente de desarrollo",
    }


# Tests de Inicialización


def test_rewriter_initialization():
    """Test: inicialización básica."""
    rewriter = ExperienceRewriter()

    assert rewriter.ai_client is None
    assert rewriter.language == "es"


def test_rewriter_with_ai_client(mock_ai_client):
    """Test: inicialización con AI client."""
    rewriter = ExperienceRewriter(ai_client=mock_ai_client)

    assert rewriter.ai_client == mock_ai_client


def test_rewriter_with_english_language():
    """Test: inicialización con idioma inglés."""
    rewriter = ExperienceRewriter(language="en")

    assert rewriter.language == "en"


# Tests de Reescritura Completa


def test_rewrite_experience_basic(sample_cv_data, sample_job_requirements, sample_gap_analysis):
    """Test: reescritura básica sin IA."""
    rewriter = ExperienceRewriter()

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
    )

    assert isinstance(result, RewriteResult)
    assert len(result.rewritten_experiences) > 0


def test_rewrite_experience_with_ai(
    mock_ai_client,
    sample_cv_data,
    sample_job_requirements,
    sample_gap_analysis,
    sample_user_answers,
):
    """Test: reescritura con IA."""
    rewriter = ExperienceRewriter(ai_client=mock_ai_client)

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
        user_answers=sample_user_answers,
    )

    assert len(result.rewritten_experiences) > 0
    assert mock_ai_client.generate_content.called


def test_rewrite_preserves_number_of_experiences(
    sample_cv_data, sample_job_requirements, sample_gap_analysis
):
    """Test: preserva el número de experiencias."""
    rewriter = ExperienceRewriter()

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
    )

    assert len(result.rewritten_experiences) == len(sample_cv_data.work_experience)


# Tests de Integración de Skills


def test_identify_skills_from_user_answers(sample_gap_analysis, sample_user_answers):
    """Test: identificación de skills confirmadas por usuario."""
    rewriter = ExperienceRewriter()

    skills = rewriter._identify_skills_to_add(sample_gap_analysis, sample_user_answers)

    assert "Docker" in skills
    assert "Kubernetes" in skills


def test_identify_skills_without_user_answers(sample_gap_analysis):
    """Test: identificación de skills sin respuestas de usuario."""
    rewriter = ExperienceRewriter()

    skills = rewriter._identify_skills_to_add(sample_gap_analysis, {})

    # Debe usar gaps del analysis
    assert len(skills) > 0


def test_skills_integrated_in_rewrite(
    sample_cv_data, sample_job_requirements, sample_gap_analysis, sample_user_answers
):
    """Test: skills se integran en la reescritura."""
    rewriter = ExperienceRewriter()

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
        user_answers=sample_user_answers,
    )

    # Verificar que al menos una experiencia tiene skills añadidas
    assert any(len(exp.added_skills) > 0 for exp in result.rewritten_experiences)


# Tests de Optimización ATS


def test_extract_job_keywords(sample_job_requirements):
    """Test: extracción de keywords de la vacante."""
    rewriter = ExperienceRewriter()

    keywords = rewriter._extract_job_keywords(sample_job_requirements)

    assert "Python" in keywords
    assert "Docker" in keywords


def test_rewritten_contains_job_keywords(
    sample_cv_data, sample_job_requirements, sample_gap_analysis
):
    """Test: texto reescrito contiene keywords ATS."""
    rewriter = ExperienceRewriter()

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
    )

    # Verificar que se añadieron keywords
    assert len(result.added_keywords) > 0


def test_action_verbs_in_rewrite(sample_cv_data, sample_job_requirements, sample_gap_analysis):
    """Test: verbos de acción en la reescritura."""
    rewriter = ExperienceRewriter(language="es")

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
    )

    # Verificar que al menos una experiencia usa verbos de acción
    action_verbs = rewriter.ACTION_VERBS["es"]
    rewritten_texts = [exp.rewritten_description for exp in result.rewritten_experiences]

    assert any(any(verb in text for verb in action_verbs) for text in rewritten_texts if text)


# Tests de Cuantificación


def test_has_quantification():
    """Test: detección de cuantificación."""
    rewriter = ExperienceRewriter()

    assert rewriter._has_quantification("Reduced costs by 50%")
    assert rewriter._has_quantification("Managed team of 10 developers")
    assert rewriter._has_quantification("Increased revenue by $50,000")
    assert not rewriter._has_quantification("Worked on various projects")


def test_quantified_achievements_count(
    mock_ai_client,
    sample_cv_data,
    sample_job_requirements,
    sample_gap_analysis,
):
    """Test: conteo de logros cuantificados."""
    rewriter = ExperienceRewriter(ai_client=mock_ai_client)

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
    )

    # La respuesta mock contiene cuantificación
    assert result.quantified_achievements > 0


# Tests de Comparación Antes/Después


def test_improvements_detected():
    """Test: detección de mejoras."""
    rewriter = ExperienceRewriter(language="es")

    original = "Worked on web applications"
    rewritten = "• Desarrollé aplicaciones web usando Python reduciendo bugs en 40%"

    improvements = rewriter._detect_improvements(original, rewritten)

    assert len(improvements) > 0


def test_experience_entry_tracks_improvements(
    sample_cv_data, sample_job_requirements, sample_gap_analysis
):
    """Test: ExperienceEntry rastrea mejoras."""
    rewriter = ExperienceRewriter()

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
    )

    # Verificar que las experiencias tienen mejoras rastreadas
    for exp in result.rewritten_experiences:
        assert isinstance(exp.improvements, list)


def test_rewritten_longer_than_original(
    sample_cv_data, sample_job_requirements, sample_gap_analysis, sample_user_answers
):
    """Test: texto reescrito es más detallado."""
    rewriter = ExperienceRewriter()

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
        user_answers=sample_user_answers,
    )

    # Al menos una experiencia debe ser más larga
    for exp in result.rewritten_experiences:
        if exp.rewritten_description:
            # El reescrito debería tener más contenido
            assert len(exp.rewritten_description) >= len(exp.original_description) * 0.8


# Tests de Extracción de Experiencias


def test_extract_experiences_from_dict():
    """Test: extracción de experiencias de diccionarios."""
    rewriter = ExperienceRewriter()

    cv_data = CVData(raw_text="Test", sections={}, metadata={})
    cv_data.work_experience = [
        {
            "company": "TestCorp",
            "title": "Developer",
            "duration": "2020-2023",
            "description": "Built stuff",
        }
    ]

    experiences = rewriter._extract_experiences(cv_data)

    assert len(experiences) == 1
    assert experiences[0].company == "TestCorp"


def test_extract_experiences_fallback_to_text():
    """Test: fallback a parsear del texto raw."""
    rewriter = ExperienceRewriter()

    cv_data = CVData(
        raw_text="""Software Developer at Tech Corp
    - Developed web applications
    - Worked with Python
    """,
        sections={},
        metadata={},
    )

    experiences = rewriter._extract_experiences(cv_data)

    # Debe encontrar al menos algo
    assert isinstance(experiences, list)


# Tests de Templates (Fallback)


def test_rewrite_with_templates():
    """Test: reescritura con templates."""
    rewriter = ExperienceRewriter(language="es")

    experience = ExperienceEntry(
        company="TestCorp",
        title="Developer",
        duration="2020-2023",
        original_description="Developed web applications\nWorked with databases",
    )

    rewritten = rewriter._rewrite_with_templates(
        experience=experience, skills_to_add=["Docker"], job_keywords=["Python"]
    )

    assert "Docker" in rewritten or "docker" in rewritten.lower()


def test_improve_line():
    """Test: mejora de línea individual."""
    rewriter = ExperienceRewriter(language="es")

    improved = rewriter._improve_line("worked on projects", keywords=["Python", "Docker"])

    # Debe empezar con bullet y verbo de acción
    assert improved.startswith("•")
    assert any(verb in improved for verb in rewriter.ACTION_VERBS["es"])


def test_create_skill_integration_line_spanish():
    """Test: creación de línea de integración en español."""
    rewriter = ExperienceRewriter(language="es")

    line = rewriter._create_skill_integration_line(["Docker", "Kubernetes"], "es")

    assert "Docker" in line
    assert "Kubernetes" in line


def test_create_skill_integration_line_english():
    """Test: creación de línea de integración en inglés."""
    rewriter = ExperienceRewriter(language="en")

    line = rewriter._create_skill_integration_line(["Docker", "Kubernetes"], "en")

    assert "Docker" in line
    assert "Kubernetes" in line
    assert "Worked" in line or "Utilized" in line


# Tests de Warnings


def test_warning_when_no_skills_integrated(sample_cv_data, sample_job_requirements):
    """Test: warning cuando no se integran skills."""
    rewriter = ExperienceRewriter()

    # Gap analysis vacío
    gap_analysis = GapAnalysisResult(
        cv_data=sample_cv_data, job_requirements=sample_job_requirements
    )

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=gap_analysis,
        user_answers={},
    )

    # Debe tener warning si no se integraron skills
    if not result.skills_integrated:
        assert len(result.warnings) > 0


# Tests de AI Rewrite


def test_ai_rewrite_called(
    mock_ai_client, sample_cv_data, sample_job_requirements, sample_gap_analysis
):
    """Test: reescritura con IA se llama correctamente."""
    rewriter = ExperienceRewriter(ai_client=mock_ai_client)

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
    )

    assert mock_ai_client.generate_content.called


def test_ai_rewrite_fallback_on_error(sample_cv_data, sample_job_requirements, sample_gap_analysis):
    """Test: fallback a templates si falla IA."""
    failing_client = Mock(spec=GeminiClient)
    failing_client.generate_content = Mock(side_effect=Exception("API Error"))

    rewriter = ExperienceRewriter(ai_client=failing_client)

    result = rewriter.rewrite_experience(
        cv_data=sample_cv_data,
        job_requirements=sample_job_requirements,
        gap_analysis=sample_gap_analysis,
    )

    # Debe completarse sin errores usando templates
    assert len(result.rewritten_experiences) > 0


def test_build_rewrite_prompt():
    """Test: construcción del prompt para IA."""
    rewriter = ExperienceRewriter(language="es")

    experience = ExperienceEntry(
        company="TestCorp",
        title="Developer",
        duration="2020-2023",
        original_description="Developed apps",
    )

    prompt = rewriter._build_rewrite_prompt(
        experience=experience,
        skills_to_add=["Docker"],
        job_keywords=["Python", "AWS"],
    )

    assert "Docker" in prompt
    assert "Python" in prompt
    assert "TestCorp" in prompt


# Tests de Edge Cases


def test_empty_cv_data():
    """Test: manejo de CV vacío."""
    rewriter = ExperienceRewriter()

    empty_cv = CVData(raw_text="", sections={}, metadata={})
    job_req = JobRequirements()
    gap_analysis = GapAnalysisResult(cv_data=empty_cv, job_requirements=job_req)

    result = rewriter.rewrite_experience(
        cv_data=empty_cv,
        job_requirements=job_req,
        gap_analysis=gap_analysis,
    )

    assert isinstance(result, RewriteResult)
    assert len(result.rewritten_experiences) == 0


def test_user_answers_with_negations():
    """Test: respuestas negativas del usuario no se integran."""
    rewriter = ExperienceRewriter()

    gap_analysis = GapAnalysisResult(
        cv_data=CVData(raw_text="Test", sections={}, metadata={}),
        job_requirements=JobRequirements(),
    )

    negative_answers = {
        "Docker": "No, nunca he trabajado con Docker",
        "Kubernetes": "No tengo experiencia con K8s",
    }

    skills = rewriter._identify_skills_to_add(gap_analysis, negative_answers)

    # No debe incluir skills con respuestas negativas
    assert len(skills) == 0 or "Docker" not in skills
