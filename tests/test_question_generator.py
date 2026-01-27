"""
Tests simplificados para QuestionGenerator.

Valida generación de preguntas contextuales basadas en gap analysis.
"""

import pytest
from unittest.mock import Mock

from src.question_generator import QuestionGenerator, Question, QuestionGroup, Language
from src.gap_analyzer import GapAnalysisResult, SkillGap
from src.job_analyzer import RequirementPriority, Skill, SkillCategory, JobRequirements
from src.cv_parser import CVData
from src.ai_backend import GeminiClient


# Fixtures


@pytest.fixture
def mock_ai_client():
    """Mock del cliente Gemini AI."""
    client = Mock(spec=GeminiClient)
    client.generate_content = Mock(
        return_value="""1. La vacante requiere Docker pero no lo veo en tu CV. ¿Tienes experiencia con Docker?
2. Esta posición requiere Kubernetes. ¿Has trabajado con Kubernetes?
3. Se menciona AWS como requisito importante. ¿Cuál es tu nivel de experiencia con AWS?"""
    )
    return client


@pytest.fixture
def sample_gaps():
    """Lista de gaps de ejemplo."""
    return [
        SkillGap(
            skill_name="Docker",
            priority=RequirementPriority.MUST_HAVE,
            context="Container orchestration",
            found_in_cv=False,
        ),
        SkillGap(
            skill_name="Kubernetes",
            priority=RequirementPriority.NICE_TO_HAVE,
            context="Cloud deployment",
            found_in_cv=False,
        ),
        SkillGap(
            skill_name="AWS",
            priority=RequirementPriority.MUST_HAVE,
            context="Cloud platform",
            found_in_cv=False,
        ),
    ]


@pytest.fixture
def sample_gap_analysis(sample_gaps):
    """GapAnalysisResult simplificado."""
    cv_data = CVData(raw_text="Test CV", sections={}, metadata={})
    job_req = JobRequirements()

    gap_analysis = GapAnalysisResult(cv_data=cv_data, job_requirements=job_req)

    gap_analysis.technical_gaps = sample_gaps
    gap_analysis.experience_gap = 2
    gap_analysis.match_score = 60.0

    return gap_analysis


# Tests de Inicialización


def test_question_generator_initialization():
    """Test: inicialización básica."""
    generator = QuestionGenerator()

    assert generator.language == Language.SPANISH
    assert generator.ai_client is None
    assert generator.templates is not None


def test_question_generator_with_ai_client(mock_ai_client):
    """Test: inicialización con AI client."""
    generator = QuestionGenerator(ai_client=mock_ai_client)

    assert generator.ai_client == mock_ai_client


def test_question_generator_with_different_language():
    """Test: inicialización con idioma diferente."""
    generator = QuestionGenerator(language=Language.ENGLISH)

    assert generator.language == Language.ENGLISH
    assert "requires" in generator.templates["technical"].lower()


# Tests de Generación de Preguntas (Templates)


def test_generate_template_questions_basic(sample_gap_analysis):
    """Test: generación básica de preguntas con templates."""
    generator = QuestionGenerator()

    questions = generator.generate_questions(sample_gap_analysis, max_questions=3, use_ai=False)

    assert len(questions) <= 3
    assert all(isinstance(q, Question) for q in questions)


def test_generate_template_questions_prioritize_critical(sample_gap_analysis):
    """Test: priorización de gaps críticos."""
    generator = QuestionGenerator()

    questions = generator.generate_questions(
        sample_gap_analysis, max_questions=5, prioritize_critical=True, use_ai=False
    )

    if questions:
        assert questions[0].priority == RequirementPriority.MUST_HAVE


def test_generate_questions_respects_max_limit(sample_gap_analysis):
    """Test: respeta el límite máximo de preguntas."""
    generator = QuestionGenerator()

    questions = generator.generate_questions(sample_gap_analysis, max_questions=2, use_ai=False)

    assert len(questions) <= 2


def test_generate_questions_empty_gaps():
    """Test: manejo de gap analysis sin gaps."""
    generator = QuestionGenerator()

    empty_gap_analysis = GapAnalysisResult(
        cv_data=CVData(raw_text="Test", sections={}, metadata={}),
        job_requirements=JobRequirements(),
    )

    questions = generator.generate_questions(empty_gap_analysis, max_questions=5, use_ai=False)

    assert isinstance(questions, list)


# Tests de Generación con IA


def test_generate_ai_questions(mock_ai_client, sample_gap_analysis):
    """Test: generación de preguntas con IA."""
    generator = QuestionGenerator(ai_client=mock_ai_client)

    questions = generator.generate_questions(sample_gap_analysis, max_questions=3, use_ai=True)

    assert len(questions) > 0
    assert mock_ai_client.generate_content.called


def test_generate_ai_questions_fallback_on_error(sample_gap_analysis):
    """Test: fallback a templates si falla IA."""
    failing_client = Mock(spec=GeminiClient)
    failing_client.generate_content = Mock(side_effect=Exception("API Error"))

    generator = QuestionGenerator(ai_client=failing_client)

    questions = generator.generate_questions(sample_gap_analysis, max_questions=3, use_ai=True)

    assert len(questions) > 0


def test_generate_questions_no_ai_client(sample_gap_analysis):
    """Test: generación sin AI client usa templates."""
    generator = QuestionGenerator()

    questions = generator.generate_questions(sample_gap_analysis, max_questions=3, use_ai=True)

    assert len(questions) > 0


# Tests de Agrupación


def test_group_questions_by_category(sample_gap_analysis):
    """Test: agrupación de preguntas por categoría."""
    generator = QuestionGenerator()

    questions = generator.generate_questions(sample_gap_analysis, max_questions=5, use_ai=False)

    groups = generator.group_questions(questions)

    assert isinstance(groups, list)
    assert all(isinstance(g, QuestionGroup) for g in groups)


def test_question_groups_have_intro_text(sample_gap_analysis):
    """Test: grupos tienen texto de introducción."""
    generator = QuestionGenerator()

    questions = generator.generate_questions(sample_gap_analysis, max_questions=5, use_ai=False)

    groups = generator.group_questions(questions)

    if groups:
        assert any(g.intro_text for g in groups)


def test_groups_sorted_by_priority(sample_gap_analysis):
    """Test: grupos ordenados por prioridad."""
    generator = QuestionGenerator()

    questions = generator.generate_questions(sample_gap_analysis, max_questions=5, use_ai=False)

    groups = generator.group_questions(questions)

    if len(groups) > 1:
        first_score = groups[0].get_priority_score()
        second_score = groups[1].get_priority_score()
        assert first_score >= second_score


# Tests de Multi-idioma


def test_spanish_questions(sample_gap_analysis):
    """Test: preguntas en español."""
    generator = QuestionGenerator(language=Language.SPANISH)

    questions = generator.generate_questions(sample_gap_analysis, max_questions=2, use_ai=False)

    if questions:
        assert any(
            word in questions[0].text.lower() for word in ["requiere", "vacante", "experiencia"]
        )


def test_english_questions(sample_gap_analysis):
    """Test: preguntas en inglés."""
    generator = QuestionGenerator(language=Language.ENGLISH)

    questions = generator.generate_questions(sample_gap_analysis, max_questions=2, use_ai=False)

    if questions:
        assert any(
            word in questions[0].text.lower() for word in ["requires", "position", "experience"]
        )


def test_set_language_changes_templates():
    """Test: cambiar idioma actualiza templates."""
    generator = QuestionGenerator(language=Language.SPANISH)
    assert "requiere" in generator.templates["technical"]

    generator.set_language(Language.ENGLISH)
    assert "requires" in generator.templates["technical"]


# Tests de Categorización


def test_categorize_technical_skills():
    """Test: categorización de skills técnicas."""
    generator = QuestionGenerator()

    gap = SkillGap(skill_name="Docker", priority=RequirementPriority.MUST_HAVE, found_in_cv=False)

    category = generator._get_gap_category(gap)
    assert category == "technical"


def test_categorize_language_skills():
    """Test: categorización de idiomas."""
    generator = QuestionGenerator()

    gap = SkillGap(skill_name="English", priority=RequirementPriority.MUST_HAVE, found_in_cv=False)

    category = generator._get_gap_category(gap)
    assert category == "language"


def test_categorize_certifications():
    """Test: categorización de certificaciones."""
    generator = QuestionGenerator()

    gap = SkillGap(
        skill_name="AWS Certified", priority=RequirementPriority.NICE_TO_HAVE, found_in_cv=False
    )

    category = generator._get_gap_category(gap)
    assert category == "certification"


def test_categorize_soft_skills():
    """Test: categorización de soft skills."""
    generator = QuestionGenerator()

    gap = SkillGap(
        skill_name="Leadership", priority=RequirementPriority.NICE_TO_HAVE, found_in_cv=False
    )

    category = generator._get_gap_category(gap)
    assert category == "soft_skill"


# Tests de Question y QuestionGroup


def test_question_is_critical():
    """Test: detección de preguntas críticas."""
    gap = SkillGap(skill_name="Docker", priority=RequirementPriority.MUST_HAVE, found_in_cv=False)

    question = Question(
        text="Test question", gap=gap, category="technical", priority=RequirementPriority.MUST_HAVE
    )

    assert question.is_critical()


def test_question_not_critical():
    """Test: pregunta no crítica."""
    gap = SkillGap(
        skill_name="Kubernetes", priority=RequirementPriority.NICE_TO_HAVE, found_in_cv=False
    )

    question = Question(
        text="Test question",
        gap=gap,
        category="technical",
        priority=RequirementPriority.NICE_TO_HAVE,
    )

    assert not question.is_critical()


def test_question_group_add_question():
    """Test: añadir pregunta a grupo."""
    group = QuestionGroup(category="technical")

    gap = SkillGap(skill_name="Docker", priority=RequirementPriority.MUST_HAVE, found_in_cv=False)
    question = Question(
        text="Test", gap=gap, category="technical", priority=RequirementPriority.MUST_HAVE
    )

    group.add_question(question)

    assert len(group.questions) == 1


def test_question_group_priority_score():
    """Test: cálculo de score de prioridad del grupo."""
    group = QuestionGroup(category="technical")

    gap1 = SkillGap(skill_name="Docker", priority=RequirementPriority.MUST_HAVE, found_in_cv=False)
    q1 = Question(text="Q1", gap=gap1, category="technical", priority=RequirementPriority.MUST_HAVE)
    group.add_question(q1)

    gap2 = SkillGap(skill_name="K8s", priority=RequirementPriority.NICE_TO_HAVE, found_in_cv=False)
    q2 = Question(
        text="Q2", gap=gap2, category="technical", priority=RequirementPriority.NICE_TO_HAVE
    )
    group.add_question(q2)

    assert group.get_priority_score() == 15  # 10 + 5


# Tests de Experience Gap


def test_generate_experience_question(sample_gap_analysis):
    """Test: generación de pregunta sobre gap de experiencia."""
    generator = QuestionGenerator()

    exp_question = generator._create_experience_question(sample_gap_analysis)

    assert exp_question is not None
    assert exp_question.category == "experience"


def test_no_experience_question_when_no_gap():
    """Test: no genera pregunta de experiencia si no hay gap."""
    generator = QuestionGenerator()

    gap_analysis = GapAnalysisResult(
        cv_data=CVData(raw_text="Test", sections={}, metadata={}),
        job_requirements=JobRequirements(),
    )
    gap_analysis.experience_gap = 0

    exp_question = generator._create_experience_question(gap_analysis)

    assert exp_question is None


# Tests de Prompt Building (AI)


def test_build_ai_prompt_structure(sample_gap_analysis):
    """Test: estructura del prompt para IA."""
    generator = QuestionGenerator()

    gaps_summary = generator._prepare_gaps_summary(sample_gap_analysis)
    cv_summary = generator._prepare_cv_summary(sample_gap_analysis.cv_data)
    job_summary = generator._prepare_job_summary(sample_gap_analysis.job_requirements)

    prompt = generator._build_ai_prompt(
        gaps_summary=gaps_summary, cv_summary=cv_summary, job_summary=job_summary, max_questions=3
    )

    assert "estratega de carrera" in prompt.lower()
    assert "preguntas" in prompt.lower()


def test_prepare_gaps_summary(sample_gap_analysis):
    """Test: resumen de gaps."""
    generator = QuestionGenerator()

    summary = generator._prepare_gaps_summary(sample_gap_analysis)

    assert isinstance(summary, str)
    assert len(summary) > 0


# Tests de Parsing de Respuesta AI


def test_parse_ai_response_numbered_list(sample_gaps):
    """Test: parsea respuesta de IA con lista numerada."""
    generator = QuestionGenerator()

    gap_analysis = GapAnalysisResult(
        cv_data=CVData(raw_text="Test", sections={}, metadata={}),
        job_requirements=JobRequirements(),
    )
    gap_analysis.technical_gaps = sample_gaps

    ai_response = """1. ¿Tienes experiencia con Docker?
2. ¿Has trabajado con Kubernetes?
3. ¿Cuál es tu nivel con AWS?"""

    questions = generator._parse_ai_response(ai_response, gap_analysis)

    assert len(questions) == 3
    assert all(isinstance(q, Question) for q in questions)


def test_parse_ai_response_empty():
    """Test: parsea respuesta vacía de IA."""
    generator = QuestionGenerator()

    gap_analysis = GapAnalysisResult(
        cv_data=CVData(raw_text="Test", sections={}, metadata={}),
        job_requirements=JobRequirements(),
    )

    questions = generator._parse_ai_response("", gap_analysis)

    assert isinstance(questions, list)
    assert len(questions) == 0
