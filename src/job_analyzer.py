"""
Analizador de vacantes: extrae requisitos y habilidades de descripciones de trabajo.

Utiliza Gemini AI para análisis semántico avanzado.
"""
import json
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from src.ai_backend import GeminiClient, GeminiResponse
from src.prompts import PromptManager


class RequirementPriority(Enum):
    """Prioridad de un requisito."""
    MUST_HAVE = "must_have"
    NICE_TO_HAVE = "nice_to_have"
    PREFERRED = "preferred"


class SkillCategory(Enum):
    """Categoría de habilidad."""
    TECHNICAL = "technical"
    SOFT = "soft"
    LANGUAGE = "language"
    CERTIFICATION = "certification"


@dataclass
class Skill:
    """Representa una habilidad extraída."""
    name: str
    category: SkillCategory
    priority: RequirementPriority
    context: Optional[str] = None  # Contexto donde se menciona


@dataclass
class JobRequirements:
    """Requisitos extraídos de una vacante."""
    technical_skills: List[Skill] = field(default_factory=list)
    soft_skills: List[Skill] = field(default_factory=list)
    languages: List[Skill] = field(default_factory=list)
    certifications: List[Skill] = field(default_factory=list)
    experience_years: Optional[int] = None
    education_level: Optional[str] = None
    responsibilities: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)
    
    def get_must_haves(self) -> List[Skill]:
        """Retorna solo los requisitos must-have."""
        all_skills = (
            self.technical_skills + 
            self.soft_skills + 
            self.languages + 
            self.certifications
        )
        return [s for s in all_skills if s.priority == RequirementPriority.MUST_HAVE]
    
    def get_all_skills(self) -> List[Skill]:
        """Retorna todas las habilidades."""
        return (
            self.technical_skills + 
            self.soft_skills + 
            self.languages + 
            self.certifications
        )


class JobAnalyzerError(Exception):
    """Excepción base para errores del analizador."""
    pass


class JobAnalyzer:
    """
    Analizador de descripciones de vacantes.
    
    Utiliza Gemini AI para extracción semántica avanzada de requisitos.
    """
    
    # Keywords para detección básica (fallback si Gemini falla)
    MUST_HAVE_KEYWORDS = [
        'required', 'must have', 'must-have', 'mandatory', 'essential',
        'requerido', 'obligatorio', 'esencial', 'indispensable',
        'exigido', 'necessário', 'obrigatório',
        'requis', 'obligatoire', 'essentiel'
    ]
    
    NICE_TO_HAVE_KEYWORDS = [
        'nice to have', 'nice-to-have', 'preferred', 'desirable', 'plus', 'bonus',
        'preferible', 'deseable', 'valorable', 'se valora',
        'preferível', 'desejável',
        'préféré', 'souhaitable'
    ]
    
    TECHNICAL_SKILL_INDICATORS = [
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'go', 'rust',
        'react', 'angular', 'vue', 'node', 'django', 'flask', 'spring',
        'sql', 'mysql', 'postgresql', 'mongodb', 'redis',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform',
        'git', 'ci/cd', 'jenkins', 'github actions',
        'machine learning', 'deep learning', 'ai', 'data science'
    ]
    
    SOFT_SKILL_INDICATORS = [
        'leadership', 'communication', 'teamwork', 'problem solving',
        'liderazgo', 'comunicación', 'trabajo en equipo', 'resolución de problemas',
        'liderança', 'comunicação', 'trabalho em equipe',
        'leadership', 'communication', 'travail d\'équipe'
    ]
    
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        """
        Inicializa el analizador de vacantes.
        
        Args:
            gemini_client: Cliente de Gemini opcional. Si no se proporciona, crea uno nuevo.
        """
        self.client = gemini_client or GeminiClient()
    
    def analyze(
        self,
        job_description: str,
        use_ai: bool = True
    ) -> JobRequirements:
        """
        Analiza una descripción de vacante y extrae requisitos.
        
        Args:
            job_description: Texto de la descripción de vacante
            use_ai: Si debe usar Gemini AI (True) o solo regex (False)
            
        Returns:
            JobRequirements con los requisitos extraídos
            
        Raises:
            JobAnalyzerError: Si hay error en el análisis
        """
        if not job_description or not job_description.strip():
            raise JobAnalyzerError("La descripción de la vacante está vacía")
        
        if use_ai:
            try:
                return self._analyze_with_ai(job_description)
            except Exception as e:
                # Fallback a análisis básico si falla AI
                print(f"Warning: Gemini AI falló, usando análisis básico. Error: {e}")
                return self._analyze_basic(job_description)
        else:
            return self._analyze_basic(job_description)
    
    def _analyze_with_ai(self, job_description: str) -> JobRequirements:
        """
        Analiza usando Gemini AI para extracción semántica avanzada.
        
        Args:
            job_description: Descripción de la vacante
            
        Returns:
            JobRequirements extraídos
        """
        prompt = self._build_analysis_prompt(job_description)
        
        response = self.client.generate(prompt, retry=True)
        
        if not response.success:
            raise JobAnalyzerError(f"Error en Gemini AI: {response.error}")
        
        # Parsear respuesta JSON
        try:
            data = self._extract_json_from_response(response.text)
            return self._parse_ai_response(data)
        except json.JSONDecodeError as e:
            raise JobAnalyzerError(f"Error parseando respuesta de AI: {e}")
    
    def _build_analysis_prompt(self, job_description: str) -> str:
        """Construye el prompt para Gemini AI."""
        return PromptManager.get_job_analysis_prompt(job_description)
    
    def _extract_json_from_response(self, text: str) -> Dict:
        """Extrae JSON de la respuesta de AI."""
        # Intentar encontrar JSON entre ```json o ```
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            json_str = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            json_str = text[start:end].strip()
        else:
            # Intentar parsear todo el texto
            json_str = text.strip()
        
        return json.loads(json_str)
    
    def _parse_ai_response(self, data: Dict) -> JobRequirements:
        """Parsea la respuesta de AI a JobRequirements."""
        
        def parse_skills(skills_data: List[Dict], category: SkillCategory) -> List[Skill]:
            skills = []
            for skill_dict in skills_data:
                priority = RequirementPriority(skill_dict.get('priority', 'nice_to_have'))
                skills.append(Skill(
                    name=skill_dict['name'],
                    category=category,
                    priority=priority,
                    context=skill_dict.get('context')
                ))
            return skills
        
        return JobRequirements(
            technical_skills=parse_skills(
                data.get('technical_skills', []), 
                SkillCategory.TECHNICAL
            ),
            soft_skills=parse_skills(
                data.get('soft_skills', []), 
                SkillCategory.SOFT
            ),
            languages=parse_skills(
                data.get('languages', []), 
                SkillCategory.LANGUAGE
            ),
            certifications=parse_skills(
                data.get('certifications', []), 
                SkillCategory.CERTIFICATION
            ),
            experience_years=data.get('experience_years'),
            education_level=data.get('education_level'),
            responsibilities=data.get('responsibilities', []),
            benefits=data.get('benefits', [])
        )
    
    def _analyze_basic(self, job_description: str) -> JobRequirements:
        """
        Análisis básico usando regex y keywords (fallback).
        
        Args:
            job_description: Descripción de la vacante
            
        Returns:
            JobRequirements extraídos
        """
        text_lower = job_description.lower()
        
        # Extraer habilidades técnicas
        technical_skills = []
        for tech in self.TECHNICAL_SKILL_INDICATORS:
            if tech in text_lower:
                priority = self._infer_priority(job_description, tech)
                technical_skills.append(Skill(
                    name=tech.title(),
                    category=SkillCategory.TECHNICAL,
                    priority=priority
                ))
        
        # Extraer habilidades blandas
        soft_skills = []
        for soft in self.SOFT_SKILL_INDICATORS:
            if soft in text_lower:
                priority = self._infer_priority(job_description, soft)
                soft_skills.append(Skill(
                    name=soft.title(),
                    category=SkillCategory.SOFT,
                    priority=priority
                ))
        
        # Extraer años de experiencia
        experience_years = self._extract_experience_years(job_description)
        
        return JobRequirements(
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            experience_years=experience_years
        )
    
    def _infer_priority(self, text: str, skill: str) -> RequirementPriority:
        """
        Infiere la prioridad de una habilidad basándose en el contexto.
        
        Args:
            text: Texto completo
            skill: Habilidad a buscar
            
        Returns:
            RequirementPriority inferida
        """
        # Buscar contexto alrededor de la habilidad
        text_lower = text.lower()
        skill_index = text_lower.find(skill.lower())
        
        if skill_index == -1:
            return RequirementPriority.NICE_TO_HAVE
        
        # Obtener contexto (100 caracteres antes y después)
        start = max(0, skill_index - 100)
        end = min(len(text), skill_index + len(skill) + 100)
        context = text_lower[start:end]
        
        # Buscar keywords de must-have
        for keyword in self.MUST_HAVE_KEYWORDS:
            if keyword in context:
                return RequirementPriority.MUST_HAVE
        
        # Buscar keywords de nice-to-have
        for keyword in self.NICE_TO_HAVE_KEYWORDS:
            if keyword in context:
                return RequirementPriority.NICE_TO_HAVE
        
        # Por defecto, considerar must-have si no hay indicadores claros
        return RequirementPriority.MUST_HAVE
    
    def _extract_experience_years(self, text: str) -> Optional[int]:
        """
        Extrae años de experiencia requeridos.
        
        Args:
            text: Texto de la descripción
            
        Returns:
            Número de años o None
        """
        # Patrones comunes para años de experiencia
        patterns = [
            r'(\d+)\+?\s*(?:years?|años|anos|ans)\s+(?:of\s+)?experience',
            r'experience.*?(\d+)\+?\s*(?:years?|años|anos|ans)',
            r'(\d+)\+?\s*(?:years?|años|anos|ans)',
        ]
        
        text_lower = text.lower()
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def get_summary(self, requirements: JobRequirements) -> Dict[str, any]:
        """
        Genera un resumen de los requisitos.
        
        Args:
            requirements: Requisitos extraídos
            
        Returns:
            Diccionario con resumen
        """
        must_haves = requirements.get_must_haves()
        all_skills = requirements.get_all_skills()
        
        return {
            'total_skills': len(all_skills),
            'must_have_skills': len(must_haves),
            'nice_to_have_skills': len(all_skills) - len(must_haves),
            'technical_skills_count': len(requirements.technical_skills),
            'soft_skills_count': len(requirements.soft_skills),
            'languages_count': len(requirements.languages),
            'certifications_count': len(requirements.certifications),
            'experience_years': requirements.experience_years,
            'has_education_requirement': requirements.education_level is not None,
            'responsibilities_count': len(requirements.responsibilities),
            'benefits_count': len(requirements.benefits)
        }
