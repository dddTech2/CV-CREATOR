"""
Generador de preguntas inteligentes basadas en gaps identificados.

Genera preguntas contextuales (no genéricas) para extraer información del usuario
y llenar las brechas entre su CV y la vacante.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.gap_analyzer import GapAnalysisResult, SkillGap
from src.job_analyzer import RequirementPriority, SkillCategory
from src.ai_backend import GeminiClient
from src.prompts import PromptManager


class Language(Enum):
    """Idiomas soportados para preguntas."""

    SPANISH = "es"
    ENGLISH = "en"
    PORTUGUESE = "pt"
    FRENCH = "fr"


@dataclass
class Question:
    """Representa una pregunta generada."""

    text: str
    gap: SkillGap
    category: str  # "technical", "soft_skill", "language", "certification", "experience"
    priority: RequirementPriority
    follow_up: Optional[str] = None  # Pregunta de seguimiento opcional

    def is_critical(self) -> bool:
        """Retorna True si la pregunta es sobre un gap crítico."""
        return self.gap.is_critical()


@dataclass
class QuestionGroup:
    """Grupo de preguntas relacionadas."""

    category: str
    questions: List[Question] = field(default_factory=list)
    intro_text: Optional[str] = None

    def add_question(self, question: Question):
        """Añade una pregunta al grupo."""
        self.questions.append(question)

    def get_priority_score(self) -> int:
        """Calcula score de prioridad del grupo."""
        score = 0
        for q in self.questions:
            if q.priority == RequirementPriority.MUST_HAVE:
                score += 10
            else:
                score += 5
        return score


class QuestionGenerator:
    """Generador de preguntas estratégicas basadas en gap analysis."""

    # Templates de preguntas por idioma
    TEMPLATES = {
        Language.SPANISH: {
            "technical": "La vacante requiere {skill} pero no lo veo en tu CV. ¿Tienes experiencia con {skill}? Si es así, describe brevemente cómo lo has usado.",
            "soft_skill": "Esta posición valora mucho {skill}. ¿Podrías compartir un ejemplo donde hayas demostrado {skill}?",
            "language": "Se requiere {skill} para este puesto. ¿Cuál es tu nivel de dominio? (básico, intermedio, avanzado, nativo)",
            "certification": "La vacante menciona {skill}. ¿Cuentas con esta certificación o experiencia equivalente?",
            "experience": "Se requieren {years} años de experiencia, pero en tu CV veo {current} años. ¿Tienes experiencia adicional relevante que no hayas incluido?",
            "intro_critical": "He identificado algunos requisitos importantes (must-have) de la vacante que no aparecen claramente en tu CV:",
            "intro_nice": "También hay algunas habilidades deseables (nice-to-have) que podrían fortalecer tu candidatura:",
            "intro_experience": "Sobre tu experiencia profesional:",
        },
        Language.ENGLISH: {
            "technical": "The position requires {skill} but I don't see it in your CV. Do you have experience with {skill}? If so, briefly describe how you've used it.",
            "soft_skill": "This position highly values {skill}. Could you share an example where you've demonstrated {skill}?",
            "language": "{skill} is required for this role. What's your proficiency level? (basic, intermediate, advanced, native)",
            "certification": "The job posting mentions {skill}. Do you have this certification or equivalent experience?",
            "experience": "{years} years of experience are required, but I see {current} years in your CV. Do you have additional relevant experience not included?",
            "intro_critical": "I've identified some important must-have requirements from the job posting that aren't clearly shown in your CV:",
            "intro_nice": "There are also some nice-to-have skills that could strengthen your application:",
            "intro_experience": "About your professional experience:",
        },
        Language.PORTUGUESE: {
            "technical": "A vaga requer {skill} mas não vejo isso no seu CV. Você tem experiência com {skill}? Se sim, descreva brevemente como o usou.",
            "soft_skill": "Esta posição valoriza muito {skill}. Poderia compartilhar um exemplo onde demonstrou {skill}?",
            "language": "É necessário {skill} para esta vaga. Qual é seu nível de domínio? (básico, intermediário, avançado, nativo)",
            "certification": "A vaga menciona {skill}. Você possui esta certificação ou experiência equivalente?",
            "experience": "São necessários {years} anos de experiência, mas vejo {current} anos no seu CV. Tem experiência adicional relevante não incluída?",
            "intro_critical": "Identifiquei alguns requisitos importantes (must-have) da vaga que não aparecem claramente no seu CV:",
            "intro_nice": "Também há algumas habilidades desejáveis (nice-to-have) que poderiam fortalecer sua candidatura:",
            "intro_experience": "Sobre sua experiência profissional:",
        },
        Language.FRENCH: {
            "technical": "Le poste nécessite {skill} mais je ne le vois pas dans votre CV. Avez-vous de l'expérience avec {skill}? Si oui, décrivez brièvement comment vous l'avez utilisé.",
            "soft_skill": "Ce poste valorise beaucoup {skill}. Pourriez-vous partager un exemple où vous avez démontré {skill}?",
            "language": "{skill} est requis pour ce poste. Quel est votre niveau de maîtrise? (basique, intermédiaire, avancé, natif)",
            "certification": "L'offre mentionne {skill}. Avez-vous cette certification ou une expérience équivalente?",
            "experience": "{years} ans d'expérience sont requis, mais je vois {current} ans dans votre CV. Avez-vous une expérience supplémentaire pertinente non incluse?",
            "intro_critical": "J'ai identifié quelques exigences importantes (must-have) de l'offre qui n'apparaissent pas clairement dans votre CV:",
            "intro_nice": "Il y a aussi quelques compétences souhaitables (nice-to-have) qui pourraient renforcer votre candidature:",
            "intro_experience": "À propos de votre expérience professionnelle:",
        },
    }

    def __init__(
        self, ai_client: Optional[GeminiClient] = None, language: Language = Language.SPANISH
    ):
        """
        Inicializa el generador de preguntas.

        Args:
            ai_client: Cliente de Gemini AI (opcional, fallback a templates)
            language: Idioma para las preguntas (default: español)
        """
        self.ai_client = ai_client
        self.language = language
        self.templates = self.TEMPLATES.get(language, self.TEMPLATES[Language.SPANISH])

    def generate_questions(
        self,
        gap_analysis: GapAnalysisResult,
        max_questions: int = 10,
        prioritize_critical: bool = True,
        use_ai: bool = True,
    ) -> List[Question]:
        """
        Genera preguntas basadas en el gap analysis.

        Args:
            gap_analysis: Resultado del análisis de brechas
            max_questions: Máximo número de preguntas a generar
            prioritize_critical: Si True, prioriza gaps críticos (must-have)
            use_ai: Si True, usa IA para preguntas más contextuales

        Returns:
            Lista de preguntas generadas
        """
        questions: List[Question] = []

        # Usar IA si está disponible y se solicita
        if use_ai and self.ai_client:
            try:
                questions = self._generate_ai_questions(gap_analysis, max_questions)
                if questions:
                    return questions
            except Exception as e:
                # Fallback a templates si falla la IA
                print(f"Warning: AI question generation failed ({e}), using templates")

        # Fallback: generar preguntas con templates
        questions = self._generate_template_questions(
            gap_analysis, max_questions, prioritize_critical
        )

        return questions

    def group_questions(self, questions: List[Question]) -> List[QuestionGroup]:
        """
        Agrupa preguntas relacionadas por categoría.

        Args:
            questions: Lista de preguntas a agrupar

        Returns:
            Lista de grupos de preguntas
        """
        groups_dict: Dict[str, QuestionGroup] = {}

        for question in questions:
            category = question.category

            if category not in groups_dict:
                # Crear nuevo grupo con intro apropiado
                intro = self._get_category_intro(category, question.priority)
                groups_dict[category] = QuestionGroup(category=category, intro_text=intro)

            groups_dict[category].add_question(question)

        # Ordenar grupos por prioridad
        groups = list(groups_dict.values())
        groups.sort(key=lambda g: g.get_priority_score(), reverse=True)

        return groups

    def _generate_template_questions(
        self, gap_analysis: GapAnalysisResult, max_questions: int, prioritize_critical: bool
    ) -> List[Question]:
        """Genera preguntas usando templates predefinidos."""
        questions: List[Question] = []
        all_gaps = gap_analysis.get_all_gaps()

        # Ordenar gaps: críticos primero si prioritize_critical
        if prioritize_critical:
            all_gaps.sort(key=lambda g: (not g.is_critical(), g.skill_name))

        # Generar pregunta para cada gap
        for gap in all_gaps[:max_questions]:
            category = self._get_gap_category(gap)
            template = self.templates.get(category, self.templates["technical"])

            question_text = template.format(
                skill=gap.skill_name,
                years=gap_analysis.job_requirements.experience_years or 0,
                current=self._estimate_cv_experience_years(gap_analysis.cv_data),
            )

            question = Question(
                text=question_text, gap=gap, category=category, priority=gap.priority
            )

            questions.append(question)

        # Agregar pregunta de experiencia si hay gap
        if gap_analysis.experience_gap and gap_analysis.experience_gap > 0:
            if len(questions) < max_questions:
                exp_question = self._create_experience_question(gap_analysis)
                if exp_question:
                    questions.append(exp_question)

        return questions[:max_questions]

    def _generate_ai_questions(
        self, gap_analysis: GapAnalysisResult, max_questions: int
    ) -> List[Question]:
        """Genera preguntas contextuales usando IA."""
        if not self.ai_client:
            return []

        # Preparar contexto para la IA
        gaps_summary = self._prepare_gaps_summary(gap_analysis)
        cv_summary = self._prepare_cv_summary(gap_analysis.cv_data)
        job_summary = self._prepare_job_summary(gap_analysis.job_requirements)

        # Prompt para Gemini
        prompt = self._build_ai_prompt(
            gaps_summary=gaps_summary,
            cv_summary=cv_summary,
            job_summary=job_summary,
            max_questions=max_questions,
        )

        # Generar preguntas con IA
        response = self.ai_client.generate_content(prompt)

        # Parsear respuesta de IA
        questions = self._parse_ai_response(response, gap_analysis)

        return questions

    def _build_ai_prompt(
        self, gaps_summary: str, cv_summary: str, job_summary: str, max_questions: int
    ) -> str:
        """Construye el prompt para la IA."""
        lang_instructions = {
            Language.SPANISH: "en español",
            Language.ENGLISH: "in English",
            Language.PORTUGUESE: "em português",
            Language.FRENCH: "en français",
        }

        lang = lang_instructions.get(self.language, "en español")

        return PromptManager.get_question_generation_prompt(
            gaps_summary=gaps_summary,
            cv_summary=cv_summary,
            job_summary=job_summary,
            max_questions=max_questions,
            language=lang
        )

    def _prepare_gaps_summary(self, gap_analysis: GapAnalysisResult) -> str:
        """Prepara resumen de gaps para el prompt de IA."""
        summary_lines = []

        all_gaps = gap_analysis.get_all_gaps()
        critical_gaps = [g for g in all_gaps if g.is_critical()]

        if critical_gaps:
            summary_lines.append("**Gaps críticos (must-have):**")
            for gap in critical_gaps:
                summary_lines.append(f"  - {gap.skill_name} ({self._get_gap_category(gap)})")

        nice_to_have_gaps = [g for g in all_gaps if not g.is_critical()]
        if nice_to_have_gaps:
            summary_lines.append("\n**Gaps deseables (nice-to-have):**")
            for gap in nice_to_have_gaps[:5]:  # Limitar a 5
                summary_lines.append(f"  - {gap.skill_name} ({self._get_gap_category(gap)})")

        if gap_analysis.experience_gap and gap_analysis.experience_gap > 0:
            summary_lines.append(
                f"\n**Gap de experiencia:** Faltan {gap_analysis.experience_gap} años"
            )

        return "\n".join(summary_lines) if summary_lines else "No hay gaps significativos"

    def _prepare_cv_summary(self, cv_data) -> str:
        """Prepara resumen del CV para el prompt de IA."""
        summary_lines = []

        # Skills
        if hasattr(cv_data, "technical_skills") and cv_data.technical_skills:
            skills = [
                s.name if hasattr(s, "name") else str(s) for s in cv_data.technical_skills[:10]
            ]
            summary_lines.append(f"**Skills técnicas:** {', '.join(skills)}")

        # Experiencia
        if hasattr(cv_data, "work_experience") and cv_data.work_experience:
            exp_count = len(cv_data.work_experience)
            summary_lines.append(f"**Experiencias:** {exp_count} posiciones")

        # Educación
        if hasattr(cv_data, "education") and cv_data.education:
            edu_count = len(cv_data.education)
            summary_lines.append(f"**Educación:** {edu_count} grados")

        return "\n".join(summary_lines) if summary_lines else "CV básico"

    def _prepare_job_summary(self, job_requirements) -> str:
        """Prepara resumen de la vacante para el prompt de IA."""
        summary_lines = []

        # Skills técnicas
        if hasattr(job_requirements, "technical_skills") and job_requirements.technical_skills:
            must_haves = [
                s.name
                for s in job_requirements.technical_skills
                if s.priority == RequirementPriority.MUST_HAVE
            ]
            if must_haves:
                summary_lines.append(f"**Must-have:** {', '.join(must_haves[:5])}")

        # Experiencia
        if hasattr(job_requirements, "experience_years") and job_requirements.experience_years:
            summary_lines.append(f"**Años de experiencia:** {job_requirements.experience_years}")

        # Idiomas
        if hasattr(job_requirements, "languages") and job_requirements.languages:
            langs = [
                lang.name if hasattr(lang, "name") else str(lang)
                for lang in job_requirements.languages
            ]
            summary_lines.append(f"**Idiomas:** {', '.join(langs)}")

        return "\n".join(summary_lines) if summary_lines else "Requisitos básicos"

    def _parse_ai_response(self, response: str, gap_analysis: GapAnalysisResult) -> List[Question]:
        """Parsea la respuesta de la IA y crea objetos Question."""
        questions: List[Question] = []

        # Dividir respuesta en líneas
        lines = response.strip().split("\n")

        all_gaps = gap_analysis.get_all_gaps()
        gap_index = 0

        for line in lines:
            line = line.strip()

            # Detectar líneas numeradas (1. 2. 3. etc.)
            if line and (line[0].isdigit() or line.startswith("-")):
                # Limpiar numeración
                question_text = line.split(".", 1)[-1].strip()
                question_text = question_text.lstrip("-").strip()

                if question_text and gap_index < len(all_gaps):
                    gap = all_gaps[gap_index]
                    category = self._get_gap_category(gap)

                    question = Question(
                        text=question_text, gap=gap, category=category, priority=gap.priority
                    )

                    questions.append(question)
                    gap_index += 1

        return questions

    def _get_gap_category(self, gap: SkillGap) -> str:
        """Determina la categoría de un gap."""
        # Analizar el nombre del skill para determinar categoría
        skill_lower = gap.skill_name.lower()

        # Idiomas
        languages = [
            "english",
            "spanish",
            "french",
            "german",
            "portuguese",
            "italian",
            "inglés",
            "español",
            "francés",
            "alemán",
            "portugués",
            "italiano",
        ]
        if any(lang in skill_lower for lang in languages):
            return "language"

        # Certificaciones
        certs = [
            "certified",
            "certification",
            "certificate",
            "aws",
            "azure",
            "gcp",
            "certificado",
            "certificación",
        ]
        if any(cert in skill_lower for cert in certs):
            return "certification"

        # Soft skills
        soft_skills = [
            "leadership",
            "communication",
            "teamwork",
            "problem-solving",
            "liderazgo",
            "comunicación",
            "trabajo en equipo",
        ]
        if any(soft in skill_lower for soft in soft_skills):
            return "soft_skill"

        # Por defecto: técnica
        return "technical"

    def _get_category_intro(self, category: str, priority: RequirementPriority) -> str:
        """Obtiene el texto de introducción para una categoría."""
        if priority == RequirementPriority.MUST_HAVE:
            return self.templates.get("intro_critical", "")
        elif category == "experience":
            return self.templates.get("intro_experience", "")
        else:
            return self.templates.get("intro_nice", "")

    def _create_experience_question(self, gap_analysis: GapAnalysisResult) -> Optional[Question]:
        """Crea pregunta sobre gap de experiencia."""
        if not gap_analysis.experience_gap or gap_analysis.experience_gap <= 0:
            return None

        required_years = gap_analysis.job_requirements.experience_years or 0
        current_years = self._estimate_cv_experience_years(gap_analysis.cv_data)

        template = self.templates.get("experience", "")
        question_text = template.format(years=required_years, current=current_years)

        # Crear un gap ficticio para la experiencia
        exp_gap = SkillGap(
            skill_name=f"{required_years} years experience",
            priority=RequirementPriority.MUST_HAVE,
            context="Required professional experience",
            found_in_cv=False,
        )

        return Question(
            text=question_text,
            gap=exp_gap,
            category="experience",
            priority=RequirementPriority.MUST_HAVE,
        )

    def _estimate_cv_experience_years(self, cv_data) -> int:
        """Estima años totales de experiencia del CV."""
        # Simplificación: contar número de trabajos * 2 años promedio
        if hasattr(cv_data, "work_experience") and cv_data.work_experience:
            return len(cv_data.work_experience) * 2
        return 0

    def set_language(self, language: Language):
        """Cambia el idioma de las preguntas."""
        self.language = language
        self.templates = self.TEMPLATES.get(language, self.TEMPLATES[Language.SPANISH])
