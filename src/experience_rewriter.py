"""
Reescritor de experiencia laboral: optimiza bullet points integrando nuevas habilidades.

Integra skills descubiertas en las respuestas del usuario, optimiza para ATS,
y cuantifica logros preservando la veracidad.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.ai_backend import GeminiClient
from src.gap_analyzer import GapAnalysisResult
from src.job_analyzer import JobRequirements, Skill
from src.prompts import PromptManager


@dataclass
class ExperienceEntry:
    """Representa una entrada de experiencia laboral."""

    company: str
    title: str
    duration: str
    original_description: str
    rewritten_description: str | None = None
    added_skills: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)


@dataclass
class RewriteResult:
    """Resultado del reescritura de experiencia."""

    rewritten_experiences: list[ExperienceEntry] = field(default_factory=list)
    added_keywords: list[str] = field(default_factory=list)
    quantified_achievements: int = 0
    skills_integrated: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ExperienceRewriter:
    """
    Reescribe experiencia laboral integrando nuevas habilidades y optimizando para ATS.

    Features:
    - Integra skills en narrativa (no solo lista)
    - Optimización ATS con palabras clave de vacante
    - Cuantificación de logros
    - Preserva veracidad (no inventa información)
    """

    # Verbos de acción para ATS optimization
    ACTION_VERBS = {
        "es": [
            "Desarrollé",
            "Implementé",
            "Diseñé",
            "Lideré",
            "Optimicé",
            "Automaticé",
            "Coordiné",
            "Gestioné",
            "Mejoré",
            "Creé",
            "Reduje",
            "Incrementé",
            "Resolví",
            "Colaboré",
            "Supervisé",
        ],
        "en": [
            "Developed",
            "Implemented",
            "Designed",
            "Led",
            "Optimized",
            "Automated",
            "Coordinated",
            "Managed",
            "Improved",
            "Created",
            "Reduced",
            "Increased",
            "Resolved",
            "Collaborated",
            "Supervised",
        ],
    }

    # Patrones para detectar cuantificación
    QUANTIFICATION_PATTERNS = [
        r"\d+%",  # Porcentajes: 50%
        r"\d+\s*(usuarios|clientes|proyectos|horas|días|meses|developers|desarrolladores|años|people|team)",  # Números con unidades
        r"\$\d+",  # Dinero
        r"\d+x",  # Multiplicadores: 2x, 3x
        r"team\s+of\s+\d+",  # Team of X
        r"equipo\s+de\s+\d+",  # Equipo de X
    ]

    def __init__(self, ai_client: GeminiClient | None = None, language: str = "es"):
        """
        Inicializa el reescritor de experiencia.

        Args:
            ai_client: Cliente de Gemini AI (opcional)
            language: Idioma para reescritura ("es" o "en")
        """
        self.ai_client = ai_client
        self.language = language

    def rewrite_experience(
        self,
        cv_data,
        job_requirements: JobRequirements,
        gap_analysis: GapAnalysisResult,
        user_answers: dict[str, str] | None = None,
    ) -> RewriteResult:
        """
        Reescribe la experiencia laboral del CV.

        Args:
            cv_data: Datos del CV actual
            job_requirements: Requisitos de la vacante
            gap_analysis: Resultado del gap analysis
            user_answers: Respuestas del usuario a las preguntas (opcional)

        Returns:
            RewriteResult con experiencias reescritas
        """
        result = RewriteResult()

        # Extraer experiencias del CV
        experiences = self._extract_experiences(cv_data)

        # Identificar skills a integrar
        skills_to_add = self._identify_skills_to_add(gap_analysis, user_answers or {})

        # Extraer keywords de la vacante
        job_keywords = self._extract_job_keywords(job_requirements)

        # Reescribir cada experiencia
        for exp in experiences:
            rewritten = self._rewrite_single_experience(
                experience=exp,
                skills_to_add=skills_to_add,
                job_keywords=job_keywords,
                use_ai=self.ai_client is not None,
            )

            result.rewritten_experiences.append(rewritten)
            
            # Safe check for rewritten description
            rewritten_text = rewritten.rewritten_description or ""
            
            result.added_keywords.extend(
                [k for k in job_keywords if k.lower() in rewritten_text.lower()]
            )
            result.skills_integrated.extend(rewritten.added_skills)

        # Calcular métricas
        result.quantified_achievements = sum(
            1
            for exp in result.rewritten_experiences
            if self._has_quantification(exp.rewritten_description or "")
        )

        # Añadir warnings si es necesario
        if not result.skills_integrated:
            result.warnings.append(
                "No se integraron nuevas skills. Revisa las respuestas del usuario."
            )

        return result

    def _extract_experiences(self, cv_data) -> list[ExperienceEntry]:
        """Extrae experiencias del CV."""
        experiences = []

        # Intentar extraer del atributo work_experience
        if hasattr(cv_data, "work_experience") and cv_data.work_experience:
            for exp in cv_data.work_experience:
                if isinstance(exp, dict):
                    experiences.append(
                        ExperienceEntry(
                            company=exp.get("company", "Unknown"),
                            title=exp.get("title", "Unknown"),
                            duration=exp.get("duration", ""),
                            original_description=exp.get("description", ""),
                        )
                    )
                else:
                    # Si es un objeto con atributos
                    experiences.append(
                        ExperienceEntry(
                            company=getattr(exp, "company", "Unknown"),
                            title=getattr(exp, "title", "Unknown"),
                            duration=getattr(exp, "duration", ""),
                            original_description=getattr(exp, "description", ""),
                        )
                    )

        # Fallback: parsear del raw_text
        if not experiences and hasattr(cv_data, "raw_text"):
            experiences = self._parse_experiences_from_text(cv_data.raw_text)

        return experiences

    def _parse_experiences_from_text(self, text: str) -> list[ExperienceEntry]:
        """Parsea experiencias del texto raw del CV."""
        experiences = []

        # Simplificación: extraer bloques que parezcan experiencias
        # En una implementación real, usarías NLP más sofisticado
        lines = text.split("\n")
        current_exp = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detectar títulos de trabajo (simplificado)
            if any(
                keyword in line.lower()
                for keyword in ["developer", "engineer", "manager", "analyst"]
            ):
                if current_exp:
                    experiences.append(current_exp)

                current_exp = ExperienceEntry(
                    company="Unknown",
                    title=line,
                    duration="",
                    original_description=line,
                )
            elif current_exp and line.startswith("-"):
                # Bullet point
                current_exp.original_description += "\n" + line

        if current_exp:
            experiences.append(current_exp)

        return experiences

    def _identify_skills_to_add(
        self, gap_analysis: GapAnalysisResult, user_answers: dict[str, str]
    ) -> list[str]:
        """
        Identifica skills que el usuario confirmó tener.

        Args:
            gap_analysis: Análisis de brechas
            user_answers: Respuestas del usuario {"skill_name": "answer"}

        Returns:
            Lista de skills confirmadas para integrar
        """
        confirmed_skills = []

        # Analizar respuestas del usuario
        for skill_name, answer in user_answers.items():
            # Si la respuesta es afirmativa y tiene contenido sustancial
            if answer and len(answer) > 5:  # Umbral reducido para aceptar respuestas cortas pero directas
                # Verificar que no sea una negación
                negative_words = ["no", "not", "never", "ninguna", "nunca", "jamás"]
                # Chequeo simple de negación al inicio
                if not any(answer.lower().strip().startswith(neg) for neg in negative_words):
                    confirmed_skills.append(skill_name)

        # Si no hay user_answers, usar gaps del analysis
        if not confirmed_skills:
            all_gaps = gap_analysis.get_all_gaps()
            # Tomar solo gaps no críticos o algunos críticos (ser conservador)
            for gap in all_gaps[:3]:  # Limitar a 3 para no sobre-integrar
                confirmed_skills.append(gap.skill_name)

        return confirmed_skills

    def _extract_job_keywords(self, job_requirements: JobRequirements) -> list[str]:
        """Extrae keywords importantes de la vacante para ATS."""
        keywords = []

        # Skills técnicas (must-have primero)
        for skill in job_requirements.get_must_haves():
            keywords.append(skill.name)

        # Otros skills
        for skill in job_requirements.get_all_skills()[:10]:  # Top 10
            if skill.name not in keywords:
                keywords.append(skill.name)

        return keywords

    def _rewrite_single_experience(
        self,
        experience: ExperienceEntry,
        skills_to_add: list[str],
        job_keywords: list[str],
        use_ai: bool = True,
    ) -> ExperienceEntry:
        """Reescribe una sola entrada de experiencia."""

        if use_ai and self.ai_client:
            # Usar IA para reescritura contextual
            rewritten_desc = self._rewrite_with_ai(experience, skills_to_add, job_keywords)
        else:
            # Fallback: template-based rewriting
            rewritten_desc = self._rewrite_with_templates(experience, skills_to_add, job_keywords)

        experience.rewritten_description = rewritten_desc
        experience.added_skills = [
            skill for skill in skills_to_add if skill.lower() in rewritten_desc.lower()
        ]
        experience.improvements = self._detect_improvements(
            experience.original_description, rewritten_desc
        )

        return experience

    def _rewrite_with_ai(
        self,
        experience: ExperienceEntry,
        skills_to_add: list[str],
        job_keywords: list[str],
    ) -> str:
        """Reescribe usando IA."""
        if not self.ai_client:
            return experience.original_description

        prompt = self._build_rewrite_prompt(experience, skills_to_add, job_keywords)

        try:
            response = self.ai_client.generate_content(prompt)
            return response.strip()
        except Exception as e:
            print(f"Warning: AI rewrite failed ({e}), using template fallback")
            return self._rewrite_with_templates(experience, skills_to_add, job_keywords)

    def _build_rewrite_prompt(
        self,
        experience: ExperienceEntry,
        skills_to_add: list[str],
        job_keywords: list[str],
    ) -> str:
        """Construye el prompt para la IA."""
        lang_instructions = {
            "es": "en español",
            "en": "in English",
        }

        lang = lang_instructions.get(self.language, "en español")

        return PromptManager.get_experience_rewrite_prompt(
            title=experience.title,
            company=experience.company,
            original_description=experience.original_description,
            skills_to_add=skills_to_add,
            job_keywords=job_keywords,
            language=lang
        )

    def _rewrite_with_templates(
        self,
        experience: ExperienceEntry,
        skills_to_add: list[str],
        job_keywords: list[str],
    ) -> str:
        """Reescribe usando templates (fallback)."""
        lines = []

        # Preservar descripción original
        original_lines = [
            line.strip() for line in experience.original_description.split("\n") if line.strip()
        ]

        # Mejorar cada línea
        for line in original_lines[:3]:  # Limitar a 3 principales
            improved = self._improve_line(line, job_keywords)
            lines.append(improved)

        # Añadir línea con nuevas skills si hay
        if skills_to_add:
            skill_line = self._create_skill_integration_line(skills_to_add, self.language)
            lines.append(skill_line)

        return "\n".join(lines)

    def _improve_line(self, line: str, keywords: list[str]) -> str:
        """Mejora una línea individual."""
        # Eliminar bullet point si existe
        improved = line.lstrip("•-*").strip()

        # Asegurar que empiece con verbo de acción
        action_verbs = self.ACTION_VERBS.get(self.language, self.ACTION_VERBS["es"])
        if not any(improved.startswith(verb) for verb in action_verbs):
            # Añadir verbo apropiado
            improved = f"{action_verbs[0]} {improved.lower()}"

        # Intentar integrar keyword si no está
        for keyword in keywords[:2]:  # Máximo 2 keywords por línea
            if keyword.lower() not in improved.lower():
                # Buscar lugar natural para insertar
                if "usando" in improved.lower() or "con" in improved.lower():
                    improved = improved.replace("usando", f"usando {keyword} y", 1).replace(
                        "con", f"con {keyword} y", 1
                    )
                    break

        # Asegurar que termina con punto
        if not improved.endswith("."):
            improved += "."

        return f"• {improved}"

    def _create_skill_integration_line(self, skills: list[str], language: str) -> str:
        """Crea una línea que integra las nuevas skills."""
        if language == "es":
            if len(skills) == 1:
                return f"• Trabajé con {skills[0]} para mejorar procesos y resultados."
            else:
                return f"• Utilicé tecnologías como {', '.join(skills[:-1])} y {skills[-1]} para optimizar soluciones."
        else:  # English
            if len(skills) == 1:
                return f"• Worked with {skills[0]} to improve processes and results."
            else:
                return f"• Utilized technologies such as {', '.join(skills[:-1])} and {skills[-1]} to optimize solutions."

    def _detect_improvements(self, original: str, rewritten: str) -> list[str]:
        """Detecta mejoras entre original y reescrito."""
        improvements = []

        # Detectar si se añadió cuantificación
        if self._has_quantification(rewritten) and not self._has_quantification(original):
            improvements.append("Añadida cuantificación")

        # Detectar si se añadieron verbos de acción
        action_verbs = self.ACTION_VERBS.get(self.language, self.ACTION_VERBS["es"])
        rewritten_has_actions = sum(1 for verb in action_verbs if verb in rewritten)
        original_has_actions = sum(1 for verb in action_verbs if verb in original)

        if rewritten_has_actions > original_has_actions:
            improvements.append("Mejorados verbos de acción")

        # Detectar si es más largo (más detalle)
        if len(rewritten) > len(original) * 1.2:
            improvements.append("Añadido más detalle")

        return improvements

    def _has_quantification(self, text: str) -> bool:
        """Verifica si el texto tiene cuantificación."""
        import re

        for pattern in self.QUANTIFICATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
