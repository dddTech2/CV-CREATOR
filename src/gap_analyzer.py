"""
Motor de Gap Analysis: compara CV con vacante e identifica brechas.

Integra CVParser, JobAnalyzer y Gemini AI para análisis completo.
"""
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field

from src.cv_parser import CVParser, CVData
from src.job_analyzer import JobAnalyzer, JobRequirements, Skill, RequirementPriority
from src.ai_backend import GeminiClient, GeminiResponse


@dataclass
class SkillGap:
    """Representa una brecha de habilidad."""
    skill_name: str
    priority: RequirementPriority
    context: Optional[str] = None
    found_in_cv: bool = False
    
    def is_critical(self) -> bool:
        """Retorna True si es un gap crítico (must-have no encontrado)."""
        return self.priority == RequirementPriority.MUST_HAVE and not self.found_in_cv


@dataclass
class GapAnalysisResult:
    """Resultado del análisis de brechas."""
    cv_data: CVData
    job_requirements: JobRequirements
    
    # Skills encontradas en el CV
    skills_found: List[Skill] = field(default_factory=list)
    
    # Skills faltantes (gaps)
    technical_gaps: List[SkillGap] = field(default_factory=list)
    soft_skill_gaps: List[SkillGap] = field(default_factory=list)
    language_gaps: List[SkillGap] = field(default_factory=list)
    certification_gaps: List[SkillGap] = field(default_factory=list)
    
    # Análisis adicional
    experience_gap: Optional[int] = None  # Años faltantes
    suggested_questions: List[str] = field(default_factory=list)
    
    # Métricas
    match_score: float = 0.0  # 0-100%
    
    def get_all_gaps(self) -> List[SkillGap]:
        """Retorna todas las brechas."""
        return (
            self.technical_gaps + 
            self.soft_skill_gaps + 
            self.language_gaps + 
            self.certification_gaps
        )
    
    def get_critical_gaps(self) -> List[SkillGap]:
        """Retorna solo gaps críticos (must-haves faltantes)."""
        return [gap for gap in self.get_all_gaps() if gap.is_critical()]
    
    def get_gap_summary(self) -> Dict[str, any]:
        """Genera resumen de gaps."""
        all_gaps = self.get_all_gaps()
        critical_gaps = self.get_critical_gaps()
        
        return {
            'total_gaps': len(all_gaps),
            'critical_gaps': len(critical_gaps),
            'technical_gaps': len(self.technical_gaps),
            'soft_skill_gaps': len(self.soft_skill_gaps),
            'language_gaps': len(self.language_gaps),
            'certification_gaps': len(self.certification_gaps),
            'match_score': self.match_score,
            'experience_gap_years': self.experience_gap
        }


class GapAnalyzerError(Exception):
    """Excepción base para errores del analizador de gaps."""
    pass


class GapAnalyzer:
    """
    Motor de Gap Analysis que compara CV con vacante.
    
    Integra CVParser, JobAnalyzer y Gemini AI para identificar brechas.
    """
    
    # Umbral de similitud para considerar que una skill está en el CV
    SIMILARITY_THRESHOLD = 0.7
    
    def __init__(
        self,
        cv_parser: Optional[CVParser] = None,
        job_analyzer: Optional[JobAnalyzer] = None,
        gemini_client: Optional[GeminiClient] = None
    ):
        """
        Inicializa el motor de Gap Analysis.
        
        Args:
            cv_parser: Parser de CVs. Si no se proporciona, crea uno nuevo.
            job_analyzer: Analizador de vacantes. Si no se proporciona, crea uno nuevo.
            gemini_client: Cliente de Gemini. Si no se proporciona, crea uno nuevo.
        """
        self.cv_parser = cv_parser or CVParser()
        self.job_analyzer = job_analyzer or JobAnalyzer()
        self.gemini_client = gemini_client or GeminiClient()
    
    def analyze(
        self,
        cv_text: str,
        job_description: str,
        use_ai: bool = True
    ) -> GapAnalysisResult:
        """
        Realiza análisis completo de brechas entre CV y vacante.
        
        Args:
            cv_text: Texto del CV actual
            job_description: Descripción de la vacante
            use_ai: Si debe usar Gemini AI para análisis avanzado
            
        Returns:
            GapAnalysisResult con el análisis completo
            
        Raises:
            GapAnalyzerError: Si hay error en el análisis
        """
        if not cv_text or not cv_text.strip():
            raise GapAnalyzerError("El texto del CV está vacío")
        
        if not job_description or not job_description.strip():
            raise GapAnalyzerError("La descripción de la vacante está vacía")
        
        # 1. Parsear CV
        cv_data = self.cv_parser.parse_text(cv_text)
        
        # 2. Analizar vacante
        job_requirements = self.job_analyzer.analyze(job_description, use_ai=use_ai)
        
        # 3. Comparar y encontrar gaps
        result = self._compare_cv_with_requirements(cv_data, job_requirements)
        
        # 4. Generar preguntas sugeridas (si usa AI)
        if use_ai:
            result.suggested_questions = self._generate_questions(result)
        
        return result
    
    def _compare_cv_with_requirements(
        self,
        cv_data: CVData,
        job_requirements: JobRequirements
    ) -> GapAnalysisResult:
        """
        Compara CV con requisitos y encuentra gaps.
        
        Args:
            cv_data: Datos del CV parseado
            job_requirements: Requisitos de la vacante
            
        Returns:
            GapAnalysisResult
        """
        result = GapAnalysisResult(
            cv_data=cv_data,
            job_requirements=job_requirements
        )
        
        cv_text_lower = cv_data.raw_text.lower()
        
        # Analizar cada categoría de skills
        result.technical_gaps = self._find_skill_gaps(
            job_requirements.technical_skills,
            cv_text_lower
        )
        
        result.soft_skill_gaps = self._find_skill_gaps(
            job_requirements.soft_skills,
            cv_text_lower
        )
        
        result.language_gaps = self._find_skill_gaps(
            job_requirements.languages,
            cv_text_lower
        )
        
        result.certification_gaps = self._find_skill_gaps(
            job_requirements.certifications,
            cv_text_lower
        )
        
        # Encontrar skills que SÍ están en el CV
        all_required_skills = job_requirements.get_all_skills()
        for skill in all_required_skills:
            if self._skill_in_text(skill.name, cv_text_lower):
                result.skills_found.append(skill)
        
        # Analizar gap de experiencia
        if job_requirements.experience_years:
            cv_years = self._extract_experience_from_cv(cv_data)
            if cv_years is not None and cv_years < job_requirements.experience_years:
                result.experience_gap = job_requirements.experience_years - cv_years
        
        # Calcular match score
        result.match_score = self._calculate_match_score(result)
        
        return result
    
    def _find_skill_gaps(
        self,
        required_skills: List[Skill],
        cv_text_lower: str
    ) -> List[SkillGap]:
        """
        Encuentra gaps para una lista de skills.
        
        Args:
            required_skills: Lista de skills requeridas
            cv_text_lower: Texto del CV en lowercase
            
        Returns:
            Lista de SkillGaps
        """
        gaps = []
        
        for skill in required_skills:
            found = self._skill_in_text(skill.name, cv_text_lower)
            
            if not found:
                # Es un gap
                gaps.append(SkillGap(
                    skill_name=skill.name,
                    priority=skill.priority,
                    context=skill.context,
                    found_in_cv=False
                ))
        
        return gaps
    
    def _skill_in_text(self, skill_name: str, text: str) -> bool:
        """
        Verifica si una skill está mencionada en el texto.
        
        Usa búsqueda simple y algunas variaciones comunes.
        
        Args:
            skill_name: Nombre de la skill
            text: Texto donde buscar (en lowercase)
            
        Returns:
            True si se encuentra la skill
        """
        skill_lower = skill_name.lower()
        
        # Búsqueda directa
        if skill_lower in text:
            return True
        
        # Variaciones comunes
        variations = self._get_skill_variations(skill_lower)
        for variation in variations:
            if variation in text:
                return True
        
        return False
    
    def _get_skill_variations(self, skill: str) -> List[str]:
        """
        Genera variaciones comunes de una skill.
        
        Args:
            skill: Nombre de la skill en lowercase
            
        Returns:
            Lista de variaciones
        """
        variations = []
        
        # JavaScript → js
        skill_map = {
            'javascript': ['js', 'node.js', 'nodejs'],
            'typescript': ['ts'],
            'python': ['py'],
            'postgresql': ['postgres'],
            'kubernetes': ['k8s'],
            'react': ['reactjs', 'react.js'],
            'vue': ['vuejs', 'vue.js'],
            'angular': ['angularjs'],
        }
        
        if skill in skill_map:
            variations.extend(skill_map[skill])
        
        # Agregar versiones sin espacios/guiones
        variations.append(skill.replace(' ', ''))
        variations.append(skill.replace('-', ''))
        variations.append(skill.replace(' ', '-'))
        
        return variations
    
    def _extract_experience_from_cv(self, cv_data: CVData) -> Optional[int]:
        """
        Intenta extraer años de experiencia del CV.
        
        Args:
            cv_data: Datos del CV
            
        Returns:
            Años de experiencia o None
        """
        import re
        
        text = cv_data.raw_text.lower()
        
        # Patrones comunes
        patterns = [
            r'(\d+)\+?\s*(?:years?|años|anos|ans)\s+(?:of\s+)?(?:experience|experiencia|experiência)',
            r'experience.*?(\d+)\+?\s*(?:years?|años|anos|ans)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _calculate_match_score(self, result: GapAnalysisResult) -> float:
        """
        Calcula score de match entre CV y vacante.
        
        Args:
            result: Resultado del análisis
            
        Returns:
            Score de 0-100
        """
        all_required_skills = result.job_requirements.get_all_skills()
        
        if not all_required_skills:
            return 100.0  # Si no hay requisitos, match perfecto
        
        skills_found_count = len(result.skills_found)
        total_required = len(all_required_skills)
        
        # Score básico basado en skills encontradas
        basic_score = (skills_found_count / total_required) * 100
        
        # Penalizar por must-haves faltantes
        critical_gaps = result.get_critical_gaps()
        critical_penalty = len(critical_gaps) * 5  # -5% por cada must-have faltante
        
        # Penalizar por gap de experiencia
        experience_penalty = 0
        if result.experience_gap and result.experience_gap > 0:
            experience_penalty = min(result.experience_gap * 3, 15)  # Max -15%
        
        final_score = max(0, basic_score - critical_penalty - experience_penalty)
        
        return round(final_score, 2)
    
    def _generate_questions(self, result: GapAnalysisResult) -> List[str]:
        """
        Genera preguntas sugeridas sobre los gaps usando Gemini AI.
        
        Args:
            result: Resultado del análisis
            
        Returns:
            Lista de preguntas sugeridas
        """
        critical_gaps = result.get_critical_gaps()
        
        if not critical_gaps:
            return []
        
        # Construir prompt para Gemini
        gap_names = [gap.skill_name for gap in critical_gaps[:5]]  # Max 5 gaps
        
        prompt = f"""Basado en el análisis de brechas entre un CV y una vacante, se identificaron las siguientes habilidades críticas faltantes:

{', '.join(gap_names)}

Genera 3-5 preguntas específicas y directas para confirmar si el candidato tiene experiencia con estas habilidades.

Formato de cada pregunta:
"La vacante requiere [HABILIDAD], pero no lo veo en tu CV. ¿Tienes experiencia con [HABILIDAD]? Si es así, describe brevemente cómo lo has usado."

Retorna solo las preguntas, una por línea, numeradas.
"""
        
        try:
            response = self.gemini_client.generate(prompt, retry=True)
            
            if response.success:
                # Parsear preguntas de la respuesta
                questions = []
                for line in response.text.split('\n'):
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-')):
                        # Remover numeración
                        question = line.split('.', 1)[-1].strip()
                        if question:
                            questions.append(question)
                
                return questions[:5]  # Max 5 preguntas
        
        except Exception as e:
            print(f"Warning: No se pudieron generar preguntas con AI: {e}")
        
        # Fallback: generar preguntas básicas
        return self._generate_basic_questions(critical_gaps)
    
    def _generate_basic_questions(self, gaps: List[SkillGap]) -> List[str]:
        """
        Genera preguntas básicas sin AI (fallback).
        
        Args:
            gaps: Lista de gaps críticos
            
        Returns:
            Lista de preguntas
        """
        questions = []
        
        for gap in gaps[:5]:  # Max 5
            question = (
                f"La vacante requiere {gap.skill_name}, pero no lo veo en tu CV. "
                f"¿Tienes experiencia con {gap.skill_name}? "
                f"Si es así, describe brevemente cómo lo has usado."
            )
            questions.append(question)
        
        return questions
    
    def get_recommendations(self, result: GapAnalysisResult) -> Dict[str, List[str]]:
        """
        Genera recomendaciones basadas en el análisis.
        
        Args:
            result: Resultado del análisis
            
        Returns:
            Diccionario con recomendaciones por categoría
        """
        recommendations = {
            'critical': [],
            'important': [],
            'nice_to_have': []
        }
        
        critical_gaps = result.get_critical_gaps()
        all_gaps = result.get_all_gaps()
        
        # Recomendaciones críticas
        if critical_gaps:
            recommendations['critical'].append(
                f"Hay {len(critical_gaps)} habilidades críticas faltantes que son MUST-HAVE para la vacante."
            )
            
            for gap in critical_gaps[:3]:
                recommendations['critical'].append(
                    f"Destacar experiencia con {gap.skill_name} si la tienes."
                )
        
        # Recomendaciones importantes
        if result.experience_gap and result.experience_gap > 0:
            recommendations['important'].append(
                f"La vacante requiere {result.job_requirements.experience_years} años de experiencia. "
                f"Considera destacar toda tu experiencia relevante."
            )
        
        # Nice to have
        nice_gaps = [g for g in all_gaps if g.priority == RequirementPriority.NICE_TO_HAVE]
        if nice_gaps:
            recommendations['nice_to_have'].append(
                f"Hay {len(nice_gaps)} habilidades deseables que podrías mencionar si las tienes."
            )
        
        return recommendations
