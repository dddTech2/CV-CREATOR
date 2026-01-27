"""
Tests unitarios para el analizador de vacantes.
"""
import pytest
from unittest.mock import Mock, patch
from src.job_analyzer import (
    JobAnalyzer,
    JobRequirements,
    Skill,
    SkillCategory,
    RequirementPriority,
    JobAnalyzerError
)
from src.ai_backend import GeminiResponse


class TestSkill:
    """Tests para la clase Skill."""
    
    def test_skill_creation(self):
        """Test creación de habilidad."""
        skill = Skill(
            name="Python",
            category=SkillCategory.TECHNICAL,
            priority=RequirementPriority.MUST_HAVE,
            context="Desarrollo backend"
        )
        
        assert skill.name == "Python"
        assert skill.category == SkillCategory.TECHNICAL
        assert skill.priority == RequirementPriority.MUST_HAVE
        assert skill.context == "Desarrollo backend"


class TestJobRequirements:
    """Tests para la clase JobRequirements."""
    
    def test_get_must_haves(self):
        """Test obtención de solo must-haves."""
        requirements = JobRequirements(
            technical_skills=[
                Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                Skill("Docker", SkillCategory.TECHNICAL, RequirementPriority.NICE_TO_HAVE),
            ],
            soft_skills=[
                Skill("Liderazgo", SkillCategory.SOFT, RequirementPriority.MUST_HAVE),
            ]
        )
        
        must_haves = requirements.get_must_haves()
        
        assert len(must_haves) == 2
        assert all(s.priority == RequirementPriority.MUST_HAVE for s in must_haves)
        assert "Python" in [s.name for s in must_haves]
        assert "Liderazgo" in [s.name for s in must_haves]
        assert "Docker" not in [s.name for s in must_haves]
    
    def test_get_all_skills(self):
        """Test obtención de todas las habilidades."""
        requirements = JobRequirements(
            technical_skills=[Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE)],
            soft_skills=[Skill("Liderazgo", SkillCategory.SOFT, RequirementPriority.MUST_HAVE)],
            languages=[Skill("Inglés", SkillCategory.LANGUAGE, RequirementPriority.MUST_HAVE)],
            certifications=[Skill("AWS", SkillCategory.CERTIFICATION, RequirementPriority.NICE_TO_HAVE)]
        )
        
        all_skills = requirements.get_all_skills()
        
        assert len(all_skills) == 4


class TestJobAnalyzer:
    """Tests para la clase JobAnalyzer."""
    
    def test_init_with_client(self):
        """Test inicialización con cliente proporcionado."""
        mock_client = Mock()
        analyzer = JobAnalyzer(gemini_client=mock_client)
        
        assert analyzer.client == mock_client
    
    @patch('src.job_analyzer.GeminiClient')
    def test_init_without_client(self, mock_client_class):
        """Test inicialización sin cliente (crea uno nuevo)."""
        analyzer = JobAnalyzer()
        
        assert analyzer.client is not None
    
    def test_analyze_empty_description_raises_error(self):
        """Test que falla con descripción vacía."""
        analyzer = JobAnalyzer()
        
        with pytest.raises(JobAnalyzerError, match="descripción de la vacante está vacía"):
            analyzer.analyze("")
    
    def test_analyze_with_ai_success(self):
        """Test análisis exitoso con AI."""
        mock_client = Mock()
        
        ai_response = '''{
            "technical_skills": [
                {"name": "Python", "priority": "must_have", "context": "Backend development"},
                {"name": "Docker", "priority": "nice_to_have", "context": "Containerization"}
            ],
            "soft_skills": [
                {"name": "Leadership", "priority": "must_have", "context": "Lead team of 5"}
            ],
            "languages": [
                {"name": "English", "priority": "must_have", "context": "Advanced level"}
            ],
            "certifications": [],
            "experience_years": 5,
            "education_level": "Bachelor's in Computer Science",
            "responsibilities": ["Develop APIs", "Mentor junior devs"],
            "benefits": ["Remote work", "Health insurance"]
        }'''
        
        mock_client.generate.return_value = GeminiResponse(
            text=ai_response,
            success=True
        )
        
        analyzer = JobAnalyzer(gemini_client=mock_client)
        requirements = analyzer.analyze("Job description here")
        
        assert len(requirements.technical_skills) == 2
        assert len(requirements.soft_skills) == 1
        assert len(requirements.languages) == 1
        assert requirements.experience_years == 5
        assert requirements.education_level == "Bachelor's in Computer Science"
        assert len(requirements.responsibilities) == 2
        assert len(requirements.benefits) == 2
    
    def test_analyze_with_ai_json_in_code_block(self):
        """Test parseo de JSON en bloque de código."""
        mock_client = Mock()
        
        ai_response = '''Aquí está el análisis:
```json
{
    "technical_skills": [{"name": "Python", "priority": "must_have"}],
    "soft_skills": [],
    "languages": [],
    "certifications": [],
    "experience_years": 3,
    "responsibilities": [],
    "benefits": []
}
```'''
        
        mock_client.generate.return_value = GeminiResponse(
            text=ai_response,
            success=True
        )
        
        analyzer = JobAnalyzer(gemini_client=mock_client)
        requirements = analyzer.analyze("Job description")
        
        assert len(requirements.technical_skills) == 1
        assert requirements.technical_skills[0].name == "Python"
    
    def test_analyze_with_ai_failure_falls_back_to_basic(self):
        """Test que usa análisis básico si AI falla."""
        mock_client = Mock()
        mock_client.generate.return_value = GeminiResponse(
            text="",
            success=False,
            error="API error"
        )
        
        analyzer = JobAnalyzer(gemini_client=mock_client)
        
        job_desc = "Required: Python, Docker. 5 years experience."
        requirements = analyzer.analyze(job_desc, use_ai=True)
        
        # Debe usar análisis básico
        assert len(requirements.technical_skills) > 0
    
    def test_analyze_basic_mode(self):
        """Test análisis básico sin AI."""
        analyzer = JobAnalyzer()
        
        job_desc = """
        Senior Python Developer
        
        Required skills:
        - Python
        - Docker
        - Kubernetes
        
        Nice to have:
        - React
        
        5+ years of experience required.
        """
        
        requirements = analyzer.analyze(job_desc, use_ai=False)
        
        # Verificar que detectó Python, Docker, etc.
        skill_names = [s.name.lower() for s in requirements.technical_skills]
        assert "python" in skill_names
        assert "docker" in skill_names
        assert "kubernetes" in skill_names
        
        # Verificar años de experiencia
        assert requirements.experience_years == 5
    
    def test_infer_priority_must_have(self):
        """Test inferencia de prioridad must-have."""
        analyzer = JobAnalyzer()
        
        text = "Required skills: Python"
        priority = analyzer._infer_priority(text, "python")
        
        assert priority == RequirementPriority.MUST_HAVE
    
    def test_infer_priority_nice_to_have(self):
        """Test inferencia de prioridad nice-to-have."""
        analyzer = JobAnalyzer()
        
        text = "Nice to have: Docker experience"
        priority = analyzer._infer_priority(text, "docker")
        
        assert priority == RequirementPriority.NICE_TO_HAVE
    
    def test_infer_priority_default_must_have(self):
        """Test que por defecto es must-have si no hay indicadores."""
        analyzer = JobAnalyzer()
        
        text = "Experience with Python"
        priority = analyzer._infer_priority(text, "python")
        
        assert priority == RequirementPriority.MUST_HAVE
    
    def test_extract_experience_years_pattern1(self):
        """Test extracción de años con patrón '5+ years experience'."""
        analyzer = JobAnalyzer()
        
        text = "5+ years of experience required"
        years = analyzer._extract_experience_years(text)
        
        assert years == 5
    
    def test_extract_experience_years_pattern2(self):
        """Test extracción con patrón 'experience 3 years'."""
        analyzer = JobAnalyzer()
        
        text = "Experience with Python for at least 3 years"
        years = analyzer._extract_experience_years(text)
        
        assert years == 3
    
    def test_extract_experience_years_spanish(self):
        """Test extracción en español."""
        analyzer = JobAnalyzer()
        
        text = "Se requieren 7 años de experiencia"
        years = analyzer._extract_experience_years(text)
        
        assert years == 7
    
    def test_extract_experience_years_not_found(self):
        """Test cuando no se encuentra experiencia."""
        analyzer = JobAnalyzer()
        
        text = "Junior developer position"
        years = analyzer._extract_experience_years(text)
        
        assert years is None
    
    def test_get_summary(self):
        """Test generación de resumen."""
        requirements = JobRequirements(
            technical_skills=[
                Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                Skill("Docker", SkillCategory.TECHNICAL, RequirementPriority.NICE_TO_HAVE),
            ],
            soft_skills=[
                Skill("Leadership", SkillCategory.SOFT, RequirementPriority.MUST_HAVE)
            ],
            languages=[
                Skill("English", SkillCategory.LANGUAGE, RequirementPriority.MUST_HAVE)
            ],
            experience_years=5,
            education_level="Bachelor's",
            responsibilities=["Task 1", "Task 2"],
            benefits=["Benefit 1"]
        )
        
        analyzer = JobAnalyzer()
        summary = analyzer.get_summary(requirements)
        
        assert summary['total_skills'] == 4
        assert summary['must_have_skills'] == 3
        assert summary['nice_to_have_skills'] == 1
        assert summary['technical_skills_count'] == 2
        assert summary['soft_skills_count'] == 1
        assert summary['languages_count'] == 1
        assert summary['experience_years'] == 5
        assert summary['has_education_requirement'] is True
        assert summary['responsibilities_count'] == 2
        assert summary['benefits_count'] == 1
    
    def test_analyze_multilanguage_keywords(self):
        """Test detección de keywords en múltiples idiomas."""
        analyzer = JobAnalyzer()
        
        # Español
        text_es = "Habilidades obligatorias: Python. Deseable: Docker"
        requirements_es = analyzer.analyze(text_es, use_ai=False)
        
        # English
        text_en = "Required: Python. Nice to have: Docker"
        requirements_en = analyzer.analyze(text_en, use_ai=False)
        
        # Ambos deben detectar las skills
        assert len(requirements_es.technical_skills) > 0
        assert len(requirements_en.technical_skills) > 0
    
    def test_real_job_description_example(self):
        """Test con ejemplo de descripción real de vacante."""
        analyzer = JobAnalyzer()
        
        job_desc = """
        Senior Backend Engineer
        
        We are seeking an experienced Backend Engineer to join our team.
        
        Requirements:
        - 5+ years of experience in backend development
        - Strong proficiency in Python and Django
        - Experience with Docker and Kubernetes
        - Solid understanding of SQL databases (PostgreSQL preferred)
        - Leadership skills to mentor junior developers
        
        Nice to have:
        - Experience with AWS or GCP
        - Knowledge of React for full-stack work
        - Previous startup experience
        
        Responsibilities:
        - Design and implement REST APIs
        - Optimize database queries
        - Lead technical discussions
        
        Benefits:
        - Competitive salary
        - Remote work
        - Health insurance
        """
        
        requirements = analyzer.analyze(job_desc, use_ai=False)
        
        # Verificar skills detectadas
        skill_names = [s.name.lower() for s in requirements.technical_skills]
        assert "python" in skill_names
        assert "docker" in skill_names
        assert "kubernetes" in skill_names
        
        # Verificar experiencia
        assert requirements.experience_years == 5
    
    def test_extract_json_with_code_markers(self):
        """Test extracción de JSON con diferentes marcadores."""
        analyzer = JobAnalyzer()
        
        # Con ```json
        text1 = '```json\n{"key": "value"}\n```'
        data1 = analyzer._extract_json_from_response(text1)
        assert data1 == {"key": "value"}
        
        # Con ``` genérico
        text2 = '```\n{"key": "value"}\n```'
        data2 = analyzer._extract_json_from_response(text2)
        assert data2 == {"key": "value"}
        
        # Sin marcadores
        text3 = '{"key": "value"}'
        data3 = analyzer._extract_json_from_response(text3)
        assert data3 == {"key": "value"}
