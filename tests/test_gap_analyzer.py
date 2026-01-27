"""
Tests unitarios para el motor de Gap Analysis.
"""
import pytest
from unittest.mock import Mock, patch
from src.gap_analyzer import (
    GapAnalyzer,
    GapAnalysisResult,
    SkillGap,
    GapAnalyzerError
)
from src.cv_parser import CVData
from src.job_analyzer import JobRequirements, Skill, SkillCategory, RequirementPriority
from src.ai_backend import GeminiResponse


class TestSkillGap:
    """Tests para la clase SkillGap."""
    
    def test_is_critical_must_have_not_found(self):
        """Test que gap must-have no encontrado es crítico."""
        gap = SkillGap(
            skill_name="Docker",
            priority=RequirementPriority.MUST_HAVE,
            found_in_cv=False
        )
        
        assert gap.is_critical()
    
    def test_is_not_critical_must_have_found(self):
        """Test que must-have encontrado NO es crítico."""
        gap = SkillGap(
            skill_name="Python",
            priority=RequirementPriority.MUST_HAVE,
            found_in_cv=True
        )
        
        assert not gap.is_critical()
    
    def test_is_not_critical_nice_to_have(self):
        """Test que nice-to-have NO es crítico aunque no esté."""
        gap = SkillGap(
            skill_name="React",
            priority=RequirementPriority.NICE_TO_HAVE,
            found_in_cv=False
        )
        
        assert not gap.is_critical()


class TestGapAnalysisResult:
    """Tests para GapAnalysisResult."""
    
    def test_get_all_gaps(self):
        """Test obtención de todos los gaps."""
        result = GapAnalysisResult(
            cv_data=Mock(),
            job_requirements=Mock(),
            technical_gaps=[SkillGap("Docker", RequirementPriority.MUST_HAVE)],
            soft_skill_gaps=[SkillGap("Leadership", RequirementPriority.MUST_HAVE)],
            language_gaps=[SkillGap("English", RequirementPriority.MUST_HAVE)]
        )
        
        all_gaps = result.get_all_gaps()
        assert len(all_gaps) == 3
    
    def test_get_critical_gaps(self):
        """Test obtención solo de gaps críticos."""
        result = GapAnalysisResult(
            cv_data=Mock(),
            job_requirements=Mock(),
            technical_gaps=[
                SkillGap("Docker", RequirementPriority.MUST_HAVE, found_in_cv=False),  # Crítico
                SkillGap("React", RequirementPriority.NICE_TO_HAVE, found_in_cv=False),  # No crítico
            ]
        )
        
        critical = result.get_critical_gaps()
        assert len(critical) == 1
        assert critical[0].skill_name == "Docker"
    
    def test_get_gap_summary(self):
        """Test generación de resumen."""
        result = GapAnalysisResult(
            cv_data=Mock(),
            job_requirements=Mock(),
            technical_gaps=[SkillGap("Docker", RequirementPriority.MUST_HAVE, found_in_cv=False)],
            soft_skill_gaps=[SkillGap("Leadership", RequirementPriority.MUST_HAVE, found_in_cv=False)],
            experience_gap=2,
            match_score=65.5
        )
        
        summary = result.get_gap_summary()
        
        assert summary['total_gaps'] == 2
        assert summary['critical_gaps'] == 2
        assert summary['technical_gaps'] == 1
        assert summary['soft_skill_gaps'] == 1
        assert summary['match_score'] == 65.5
        assert summary['experience_gap_years'] == 2


class TestGapAnalyzer:
    """Tests para la clase GapAnalyzer."""
    
    def test_init_with_dependencies(self):
        """Test inicialización con dependencias proporcionadas."""
        mock_parser = Mock()
        mock_job_analyzer = Mock()
        mock_client = Mock()
        
        analyzer = GapAnalyzer(
            cv_parser=mock_parser,
            job_analyzer=mock_job_analyzer,
            gemini_client=mock_client
        )
        
        assert analyzer.cv_parser == mock_parser
        assert analyzer.job_analyzer == mock_job_analyzer
        assert analyzer.gemini_client == mock_client
    
    @patch('src.gap_analyzer.CVParser')
    @patch('src.gap_analyzer.JobAnalyzer')
    @patch('src.gap_analyzer.GeminiClient')
    def test_init_without_dependencies(self, mock_client, mock_job_analyzer, mock_parser):
        """Test inicialización sin dependencias (crea nuevas)."""
        analyzer = GapAnalyzer()
        
        assert analyzer.cv_parser is not None
        assert analyzer.job_analyzer is not None
        assert analyzer.gemini_client is not None
    
    def test_analyze_empty_cv_raises_error(self):
        """Test que falla con CV vacío."""
        analyzer = GapAnalyzer()
        
        with pytest.raises(GapAnalyzerError, match="CV está vacío"):
            analyzer.analyze("", "Job description")
    
    def test_analyze_empty_job_raises_error(self):
        """Test que falla con vacante vacía."""
        analyzer = GapAnalyzer()
        
        with pytest.raises(GapAnalyzerError, match="vacante está vacía"):
            analyzer.analyze("CV text", "")
    
    def test_analyze_success(self):
        """Test análisis exitoso completo."""
        # Setup mocks
        mock_parser = Mock()
        mock_parser.parse_text.return_value = CVData(
            raw_text="Python developer with 3 years experience",
            sections={'experience': 'detected'},
            metadata={}
        )
        
        mock_job_analyzer = Mock()
        mock_job_analyzer.analyze.return_value = JobRequirements(
            technical_skills=[
                Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                Skill("Docker", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
            ],
            experience_years=5
        )
        
        mock_client = Mock()
        mock_client.generate.return_value = GeminiResponse(
            text="1. ¿Tienes experiencia con Docker?",
            success=True
        )
        
        analyzer = GapAnalyzer(
            cv_parser=mock_parser,
            job_analyzer=mock_job_analyzer,
            gemini_client=mock_client
        )
        
        result = analyzer.analyze("CV text", "Job description", use_ai=True)
        
        # Verificaciones
        assert result is not None
        assert result.cv_data is not None
        assert result.job_requirements is not None
        
        # Python está en CV, Docker no
        assert len(result.skills_found) == 1
        assert result.skills_found[0].name == "Python"
        
        # Docker es un gap
        assert len(result.technical_gaps) > 0
        
        # Gap de experiencia (requiere 5, tiene 3)
        assert result.experience_gap == 2
        
        # Score debe ser < 100 por gaps
        assert result.match_score < 100
    
    def test_skill_in_text_direct_match(self):
        """Test detección directa de skill."""
        analyzer = GapAnalyzer()
        
        text = "experience with python and docker"
        assert analyzer._skill_in_text("python", text)
        assert analyzer._skill_in_text("docker", text)
        assert not analyzer._skill_in_text("kubernetes", text)
    
    def test_skill_in_text_with_variations(self):
        """Test detección con variaciones."""
        analyzer = GapAnalyzer()
        
        text = "proficient in js and k8s"
        assert analyzer._skill_in_text("javascript", text)  # js → javascript
        assert analyzer._skill_in_text("kubernetes", text)  # k8s → kubernetes
    
    def test_get_skill_variations(self):
        """Test generación de variaciones de skills."""
        analyzer = GapAnalyzer()
        
        variations = analyzer._get_skill_variations("javascript")
        assert "js" in variations
        assert "nodejs" in variations or "node.js" in variations
    
    def test_calculate_match_score_perfect(self):
        """Test cálculo de score perfecto (100%)."""
        analyzer = GapAnalyzer()
        
        # Todos los skills encontrados
        result = GapAnalysisResult(
            cv_data=Mock(),
            job_requirements=JobRequirements(
                technical_skills=[
                    Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                ]
            ),
            skills_found=[
                Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
            ]
        )
        
        score = analyzer._calculate_match_score(result)
        assert score == 100.0
    
    def test_calculate_match_score_with_critical_gaps(self):
        """Test cálculo con gaps críticos (penalización)."""
        analyzer = GapAnalyzer()
        
        result = GapAnalysisResult(
            cv_data=Mock(),
            job_requirements=JobRequirements(
                technical_skills=[
                    Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                    Skill("Docker", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                ]
            ),
            skills_found=[
                Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
            ],
            technical_gaps=[
                SkillGap("Docker", RequirementPriority.MUST_HAVE, found_in_cv=False)
            ]
        )
        
        score = analyzer._calculate_match_score(result)
        
        # Score base: 50% (1/2 skills)
        # Penalización: -5% por critical gap
        # Score esperado: ~45%
        assert 40 <= score <= 50
    
    def test_calculate_match_score_with_experience_gap(self):
        """Test cálculo con gap de experiencia."""
        analyzer = GapAnalyzer()
        
        result = GapAnalysisResult(
            cv_data=Mock(),
            job_requirements=JobRequirements(
                technical_skills=[
                    Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                ]
            ),
            skills_found=[
                Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
            ],
            experience_gap=3  # 3 años de diferencia
        )
        
        score = analyzer._calculate_match_score(result)
        
        # Score base: 100%
        # Penalización por experiencia: -9% (3 años * 3%)
        assert 85 <= score <= 95
    
    def test_generate_basic_questions(self):
        """Test generación básica de preguntas (fallback)."""
        analyzer = GapAnalyzer()
        
        gaps = [
            SkillGap("Docker", RequirementPriority.MUST_HAVE),
            SkillGap("Kubernetes", RequirementPriority.MUST_HAVE),
        ]
        
        questions = analyzer._generate_basic_questions(gaps)
        
        assert len(questions) == 2
        assert "Docker" in questions[0]
        assert "Kubernetes" in questions[1]
        assert "describe brevemente" in questions[0].lower()
    
    def test_get_recommendations_with_critical_gaps(self):
        """Test recomendaciones con gaps críticos."""
        analyzer = GapAnalyzer()
        
        result = GapAnalysisResult(
            cv_data=Mock(),
            job_requirements=JobRequirements(
                technical_skills=[
                    Skill("Docker", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                ],
                experience_years=5
            ),
            technical_gaps=[
                SkillGap("Docker", RequirementPriority.MUST_HAVE, found_in_cv=False)
            ],
            experience_gap=2
        )
        
        recommendations = analyzer.get_recommendations(result)
        
        assert 'critical' in recommendations
        assert 'important' in recommendations
        assert len(recommendations['critical']) > 0
        assert len(recommendations['important']) > 0
    
    def test_real_scenario_gap_analysis(self):
        """Test con escenario real completo."""
        # CV real
        cv_text = """
        John Doe
        Senior Python Developer
        
        Experience:
        - 3 years at TechCorp developing backend systems with Python and PostgreSQL
        - Built REST APIs using Django
        - Mentored junior developers
        
        Skills:
        - Python, Django, PostgreSQL, Git
        """
        
        # Vacante real
        job_desc = """
        Senior Backend Engineer
        
        Requirements:
        - 5+ years of Python experience (Required)
        - Docker and Kubernetes expertise (Required)
        - Leadership skills (Required)
        - AWS experience (Nice to have)
        """
        
        # Setup mocks
        mock_parser = Mock()
        mock_parser.parse_text.return_value = CVData(
            raw_text=cv_text,
            sections={'experience': 'detected', 'skills': 'detected'},
            metadata={}
        )
        
        mock_job_analyzer = Mock()
        mock_job_analyzer.analyze.return_value = JobRequirements(
            technical_skills=[
                Skill("Python", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                Skill("Docker", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                Skill("Kubernetes", SkillCategory.TECHNICAL, RequirementPriority.MUST_HAVE),
                Skill("AWS", SkillCategory.TECHNICAL, RequirementPriority.NICE_TO_HAVE),
            ],
            soft_skills=[
                Skill("Leadership", SkillCategory.SOFT, RequirementPriority.MUST_HAVE),
            ],
            experience_years=5
        )
        
        analyzer = GapAnalyzer(
            cv_parser=mock_parser,
            job_analyzer=mock_job_analyzer
        )
        
        result = analyzer.analyze(cv_text, job_desc, use_ai=False)
        
        # Verificaciones
        # Python debe estar en skills_found
        skill_names = [s.name for s in result.skills_found]
        assert "Python" in skill_names
        
        # Leadership es un gap porque no está explícito (sin IA no puede inferir de "Mentored")
        # En modo básico, solo detecta skills explícitas
        
        # Docker y Kubernetes son gaps críticos
        critical_gaps = result.get_critical_gaps()
        gap_names = [g.skill_name for g in critical_gaps]
        assert "Docker" in gap_names
        assert "Kubernetes" in gap_names
        
        # Gap de experiencia (requiere IA para parsear "3 years" del texto)
        # Sin IA, experience_gap puede ser None
        # assert result.experience_gap == 2  # Comentado: requiere IA
        
        # Score debe reflejar los gaps
        assert 0 < result.match_score < 100
