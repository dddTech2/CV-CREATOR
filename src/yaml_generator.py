"""
Generador de archivos YAML compatibles con RenderCV.

Genera CVs en formato YAML válido para diferentes temas y lenguajes.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import yaml

from src.cv_parser import CVData


class Theme(Enum):
    """Temas disponibles de RenderCV."""
    CLASSIC = "classic"
    SB2NOV = "sb2nov"
    MODERNCV = "moderncv"
    ENGINEERINGRESUMES = "engineeringresumes"


class Language(Enum):
    """Idiomas soportados."""
    ENGLISH = "en"
    SPANISH = "es"
    PORTUGUESE = "pt"
    FRENCH = "fr"


# Traducciones de secciones
SECTION_TRANSLATIONS = {
    Language.ENGLISH: {
        "experience": "experience",
        "education": "education",
        "skills": "skills",
        "summary": "summary",
        "projects": "projects",
        "certifications": "certifications",
        "languages": "languages"
    },
    Language.SPANISH: {
        "experience": "experiencia",
        "education": "educación",
        "skills": "habilidades",
        "summary": "resumen",
        "projects": "proyectos",
        "certifications": "certificaciones",
        "languages": "idiomas"
    },
    Language.PORTUGUESE: {
        "experience": "experiência",
        "education": "educação",
        "skills": "competências",
        "summary": "resumo",
        "projects": "projetos",
        "certifications": "certificações",
        "languages": "idiomas"
    },
    Language.FRENCH: {
        "experience": "expérience",
        "education": "éducation",
        "skills": "compétences",
        "summary": "résumé",
        "projects": "projets",
        "certifications": "certifications",
        "languages": "langues"
    }
}


class YAMLGeneratorError(Exception):
    """Excepción base para errores del generador YAML."""
    pass


class YAMLValidationError(YAMLGeneratorError):
    """Excepción para errores de validación YAML."""
    pass


@dataclass
class ContactInfo:
    """Información de contacto del CV."""
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    website: str | None = None
    linkedin: str | None = None
    github: str | None = None


@dataclass
class ExperienceEntry:
    """Entrada de experiencia laboral."""
    company: str
    position: str
    start_date: str
    end_date: str = "present"
    location: str | None = None
    highlights: list[str] | None = None


@dataclass
class EducationEntry:
    """Entrada de educación."""
    institution: str
    degree: str
    area: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    highlights: list[str] | None = None


@dataclass
class SkillEntry:
    """Entrada de habilidad."""
    label: str
    details: str


@dataclass
class ProjectEntry:
    """Entrada de proyecto."""
    name: str
    summary: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    location: str | None = None
    highlights: list[str] | None = None


class YAMLGenerator:
    """
    Generador de archivos YAML compatibles con RenderCV.
    
    Soporta múltiples temas y lenguajes, con validación sintáctica.
    """

    def __init__(self):
        """Inicializa el generador YAML."""
        self.supported_themes = [theme.value for theme in Theme]
        self.supported_languages = [lang.value for lang in Language]

    def generate(
        self,
        cv_data: CVData,
        theme: str = "classic",
        language: str = "en",
        contact_info: ContactInfo | None = None,
        experience: list[ExperienceEntry] | None = None,
        education: list[EducationEntry] | None = None,
        skills: list[SkillEntry] | None = None,
        projects: list[ProjectEntry] | None = None,
        summary: str | None = None
    ) -> str:
        """
        Genera un YAML compatible con RenderCV.
        
        Args:
            cv_data: Datos parseados del CV
            theme: Tema de RenderCV (classic, sb2nov, moderncv, engineeringresumes)
            language: Idioma del CV (en, es, pt, fr)
            contact_info: Información de contacto
            experience: Lista de experiencias laborales
            education: Lista de educación
            skills: Lista de habilidades
            projects: Lista de proyectos
            summary: Resumen profesional
            education: Lista de educación
            skills: Lista de habilidades
            summary: Resumen profesional
            
        Returns:
            String con el YAML generado
            
        Raises:
            YAMLGeneratorError: Si hay error al generar el YAML
        """
        # Validar inputs
        if theme not in self.supported_themes:
            raise YAMLGeneratorError(
                f"Tema no soportado: {theme}. "
                f"Temas disponibles: {', '.join(self.supported_themes)}"
            )

        if language not in self.supported_languages:
            raise YAMLGeneratorError(
                f"Idioma no soportado: {language}. "
                f"Idiomas disponibles: {', '.join(self.supported_languages)}"
            )

        # Obtener traducciones
        lang_enum = Language(language)
        translations = SECTION_TRANSLATIONS[lang_enum]

        # Construir estructura del CV
        cv_structure = self._build_cv_structure(
            cv_data=cv_data,
            contact_info=contact_info,
            experience=experience,
            education=education,
            skills=skills,
            projects=projects,
            summary=summary,
            translations=translations
        )

        # Construir documento completo
        document = {
            "cv": cv_structure,
            "design": {
                "theme": theme
            },
            "locale": {
                "language": self._get_locale_name(language)
            }
        }

        # Convertir a YAML
        try:
            yaml_str = yaml.dump(
                document,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=120
            )

            # Añadir comentario de schema al inicio
            schema_comment = (
                "# yaml-language-server: $schema=https://raw.githubusercontent.com/"
                "rendercv/rendercv/refs/tags/v2.5/schema.json\n"
            )
            yaml_str = schema_comment + yaml_str

            return yaml_str

        except Exception as e:
            raise YAMLGeneratorError(f"Error al generar YAML: {str(e)}")

    def _build_cv_structure(
        self,
        cv_data: CVData,
        contact_info: ContactInfo | None,
        experience: list[ExperienceEntry] | None,
        education: list[EducationEntry] | None,
        skills: list[SkillEntry] | None,
        projects: list[ProjectEntry] | None,
        summary: str | None,
        translations: dict[str, str]
    ) -> dict[str, Any]:
        """
        Construye la estructura del CV.
        
        Args:
            cv_data: Datos parseados del CV
            contact_info: Información de contacto
            experience: Experiencias laborales
            education: Educación
            skills: Habilidades
            projects: Proyectos
            summary: Resumen
            translations: Traducciones de secciones
            
        Returns:
            Diccionario con estructura del CV
        """
        cv_dict = {}

        # Información básica
        if contact_info:
            cv_dict["name"] = contact_info.name
            if contact_info.location:
                cv_dict["location"] = contact_info.location
            if contact_info.email:
                cv_dict["email"] = contact_info.email
            if contact_info.phone:
                # RenderCV v2.3+ es extremadamente estricto con el formato del teléfono
                # Requiere: +[código_país][número] sin espacios ni guiones
                phone = str(contact_info.phone).strip()
                
                # Limpieza básica
                clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
                
                if clean_phone:
                    # Si no tiene +, lo agregamos proactivamente
                    if not clean_phone.startswith("+"):
                        clean_phone = "+" + clean_phone
                    
                    cv_dict["phone"] = clean_phone
            if contact_info.website:
                cv_dict["website"] = contact_info.website

            # Social networks
            social_networks = []
            if contact_info.linkedin:
                social_networks.append({
                    "network": "LinkedIn",
                    "username": contact_info.linkedin
                })
            if contact_info.github:
                social_networks.append({
                    "network": "GitHub",
                    "username": contact_info.github
                })
            if social_networks:
                cv_dict["social_networks"] = social_networks
        else:
            # Información básica por defecto
            cv_dict["name"] = "Your Name"

        # Secciones
        sections = {}

        # Resumen
        if summary:
            sections[translations["summary"]] = [summary]

        # Experiencia
        if experience:
            experience_list = []
            for exp in experience:
                exp_dict: dict[str, Any] = {
                    "company": exp.company,
                    "position": exp.position,
                    "start_date": exp.start_date,
                    "end_date": exp.end_date
                }
                if exp.location:
                    exp_dict["location"] = exp.location
                if exp.highlights:
                    exp_dict["highlights"] = exp.highlights
                experience_list.append(exp_dict)
            sections[translations["experience"]] = experience_list

        # Proyectos (después de experiencia)
        if projects:
            projects_list = []
            for project in projects:
                proj_dict: dict[str, Any] = {
                    "name": project.name
                }
                if project.summary:
                    proj_dict["summary"] = project.summary
                if project.start_date:
                    proj_dict["start_date"] = project.start_date
                if project.end_date:
                    proj_dict["end_date"] = project.end_date
                if project.location:
                    proj_dict["location"] = project.location
                if project.highlights:
                    proj_dict["highlights"] = project.highlights
                projects_list.append(proj_dict)
            sections[translations["projects"]] = projects_list

        # Educación
        if education:
            education_list = []
            for edu in education:
                edu_dict: dict[str, Any] = {
                    "institution": edu.institution,
                    "degree": edu.degree
                }
                
                # RenderCV requiere el campo 'area'. Si no existe, usamos el degree como fallback.
                if edu.area:
                    edu_dict["area"] = edu.area
                else:
                    edu_dict["area"] = edu.degree
                
                if edu.start_date:
                    edu_dict["start_date"] = edu.start_date
                if edu.end_date:
                    edu_dict["end_date"] = edu.end_date
                if edu.location:
                    edu_dict["location"] = edu.location
                if edu.highlights:
                    edu_dict["highlights"] = edu.highlights
                education_list.append(edu_dict)
            sections[translations["education"]] = education_list

        # Habilidades
        if skills:
            skills_list = []
            for skill in skills:
                skills_list.append({
                    "label": skill.label,
                    "details": skill.details
                })
            sections[translations["skills"]] = skills_list

        if sections:
            cv_dict["sections"] = sections

        return cv_dict

    def _get_locale_name(self, language: str) -> str:
        """
        Obtiene el nombre completo del idioma para RenderCV.
        
        Args:
            language: Código de idioma (en, es, pt, fr)
            
        Returns:
            Nombre completo del idioma (english, spanish, etc.)
        """
        # Mapeo de códigos a nombres completos según schema de RenderCV
        locale_map = {
            "en": "english",
            "es": "spanish",
            "pt": "portuguese",
            "fr": "french",
            "de": "german",
            "it": "italian",
            "nl": "dutch",
            "tr": "turkish"
        }
        
        return locale_map.get(language.lower(), "english")

    def validate_yaml(self, yaml_str: str) -> bool:
        """
        Valida que una cadena YAML tenga sintaxis correcta.
        
        Args:
            yaml_str: String con contenido YAML
            
        Returns:
            True si el YAML es válido sintácticamente
            
        Raises:
            YAMLValidationError: Si el YAML es inválido
        """
        if not yaml_str or not yaml_str.strip():
            raise YAMLValidationError("El YAML está vacío")

        try:
            # Intentar parsear el YAML
            parsed = yaml.safe_load(yaml_str)

            # Verificar que se parseó algo
            if parsed is None:
                raise YAMLValidationError("El YAML no contiene datos válidos")

            # Verificar estructura básica de RenderCV
            if not isinstance(parsed, dict):
                raise YAMLValidationError("El YAML debe ser un diccionario")

            if "cv" not in parsed:
                raise YAMLValidationError("El YAML debe contener la clave 'cv'")

            cv_section = parsed["cv"]
            if not isinstance(cv_section, dict):
                raise YAMLValidationError("La sección 'cv' debe ser un diccionario")

            if "name" not in cv_section:
                raise YAMLValidationError("La sección 'cv' debe contener 'name'")

            return True

        except yaml.YAMLError as e:
            raise YAMLValidationError(f"Error de sintaxis YAML: {str(e)}")
        except Exception as e:
            if isinstance(e, YAMLValidationError):
                raise
            raise YAMLValidationError(f"Error al validar YAML: {str(e)}")

    def generate_from_text(
        self,
        name: str,
        cv_text: str,
        theme: str = "classic",
        language: str = "en"
    ) -> str:
        """
        Genera YAML básico a partir de texto plano.
        
        Esta es una función de conveniencia para casos simples.
        
        Args:
            name: Nombre de la persona
            cv_text: Texto del CV
            theme: Tema de RenderCV
            language: Idioma
            
        Returns:
            String con YAML generado
        """
        # Crear CVData simple
        from src.cv_parser import CVData
        cv_data = CVData(
            raw_text=cv_text,
            sections={},
            metadata={"format": "text"}
        )

        # Crear ContactInfo básico
        contact = ContactInfo(name=name)

        # Generar YAML
        return self.generate(
            cv_data=cv_data,
            theme=theme,
            language=language,
            contact_info=contact
        )

    def parse_and_generate(
        self,
        structured_data: dict[str, Any],
        theme: str = "classic",
        language: str = "en"
    ) -> str:
        """
        Genera YAML a partir de datos estructurados.
        
        Args:
            structured_data: Diccionario con datos estructurados del CV
                Estructura esperada:
                {
                    "name": str,
                    "email": str (optional),
                    "phone": str (optional),
                    "location": str (optional),
                    "linkedin": str (optional),
                    "github": str (optional),
                    "summary": str (optional),
                    "experience": [
                        {
                            "company": str,
                            "position": str,
                            "start_date": str,
                            "end_date": str,
                            "location": str (optional),
                            "highlights": [str] (optional)
                        }
                    ] (optional),
                    "education": [
                        {
                            "institution": str,
                            "degree": str,
                            "area": str (optional),
                            "start_date": str (optional),
                            "end_date": str (optional),
                            "location": str (optional),
                            "highlights": [str] (optional)
                        }
                    ] (optional),
                    "skills": [
                        {"label": str, "details": str}
                    ] (optional)
                }
            theme: Tema de RenderCV
            language: Idioma
            
        Returns:
            String con YAML generado
            
        Raises:
            YAMLGeneratorError: Si faltan campos requeridos
        """
        if "name" not in structured_data:
            raise YAMLGeneratorError("El campo 'name' es requerido")

        # Crear ContactInfo
        contact = ContactInfo(
            name=structured_data["name"],
            email=structured_data.get("email"),
            phone=structured_data.get("phone"),
            location=structured_data.get("location"),
            linkedin=structured_data.get("linkedin"),
            github=structured_data.get("github")
        )

        # Convertir experience
        experience = None
        if "experience" in structured_data:
            experience = [
                ExperienceEntry(**exp_data)
                for exp_data in structured_data["experience"]
            ]

        # Convertir education
        education = None
        if "education" in structured_data:
            education = [
                EducationEntry(**edu_data)
                for edu_data in structured_data["education"]
            ]

        # Convertir skills
        skills = None
        if "skills" in structured_data:
            skills = [
                SkillEntry(**skill_data)
                for skill_data in structured_data["skills"]
            ]

        # Convertir projects
        projects = None
        if "projects" in structured_data:
            projects = [
                ProjectEntry(**proj_data)
                for proj_data in structured_data["projects"]
            ]

        # Obtener summary
        summary = structured_data.get("summary")

        # Crear CVData dummy
        from src.cv_parser import CVData
        cv_data = CVData(
            raw_text="",
            sections={},
            metadata={"format": "structured"}
        )

        # Generar YAML
        return self.generate(
            cv_data=cv_data,
            theme=theme,
            language=language,
            contact_info=contact,
            experience=experience,
            education=education,
            skills=skills,
            projects=projects,
            summary=summary
        )
