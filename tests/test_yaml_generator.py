"""
Tests unitarios para el generador de YAML.
"""
import pytest
import yaml

from src.cv_parser import CVData
from src.yaml_generator import (
    SECTION_TRANSLATIONS,
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    Language,
    SkillEntry,
    Theme,
    YAMLGenerator,
    YAMLGeneratorError,
    YAMLValidationError,
)


class TestEnums:
    """Tests para los enums."""

    def test_theme_enum_values(self):
        """Test valores del enum Theme."""
        assert Theme.CLASSIC.value == "classic"
        assert Theme.SB2NOV.value == "sb2nov"
        assert Theme.MODERNCV.value == "moderncv"
        assert Theme.ENGINEERINGRESUMES.value == "engineeringresumes"

    def test_language_enum_values(self):
        """Test valores del enum Language."""
        assert Language.ENGLISH.value == "en"
        assert Language.SPANISH.value == "es"
        assert Language.PORTUGUESE.value == "pt"
        assert Language.FRENCH.value == "fr"


class TestSectionTranslations:
    """Tests para las traducciones de secciones."""

    def test_all_languages_have_same_keys(self):
        """Test que todos los idiomas tienen las mismas claves."""
        keys_sets = [set(translations.keys()) for translations in SECTION_TRANSLATIONS.values()]
        assert all(keys == keys_sets[0] for keys in keys_sets)

    def test_spanish_translations(self):
        """Test traducciones al español."""
        spanish = SECTION_TRANSLATIONS[Language.SPANISH]
        assert spanish["experience"] == "experiencia"
        assert spanish["education"] == "educación"
        assert spanish["skills"] == "habilidades"
        assert spanish["summary"] == "resumen"

    def test_english_translations(self):
        """Test traducciones al inglés."""
        english = SECTION_TRANSLATIONS[Language.ENGLISH]
        assert english["experience"] == "experience"
        assert english["education"] == "education"
        assert english["skills"] == "skills"


class TestDataClasses:
    """Tests para las dataclasses."""

    def test_contact_info_creation(self):
        """Test creación de ContactInfo."""
        contact = ContactInfo(
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            location="New York, USA",
            linkedin="johndoe",
            github="johndoe"
        )
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"
        assert contact.linkedin == "johndoe"

    def test_contact_info_minimal(self):
        """Test ContactInfo con campos mínimos."""
        contact = ContactInfo(name="Jane Smith")
        assert contact.name == "Jane Smith"
        assert contact.email is None
        assert contact.phone is None

    def test_experience_entry_creation(self):
        """Test creación de ExperienceEntry."""
        exp = ExperienceEntry(
            company="Tech Corp",
            position="Software Engineer",
            start_date="2020-01",
            end_date="2023-12",
            location="San Francisco, CA",
            highlights=["Built feature X", "Led team Y"]
        )
        assert exp.company == "Tech Corp"
        assert exp.position == "Software Engineer"
        assert len(exp.highlights) == 2

    def test_education_entry_creation(self):
        """Test creación de EducationEntry."""
        edu = EducationEntry(
            institution="MIT",
            degree="BS",
            area="Computer Science",
            start_date="2016",
            end_date="2020"
        )
        assert edu.institution == "MIT"
        assert edu.degree == "BS"
        assert edu.area == "Computer Science"

    def test_skill_entry_creation(self):
        """Test creación de SkillEntry."""
        skill = SkillEntry(
            label="Programming",
            details="Python, JavaScript, Go"
        )
        assert skill.label == "Programming"
        assert skill.details == "Python, JavaScript, Go"


class TestYAMLGeneratorInit:
    """Tests para inicialización de YAMLGenerator."""

    def test_init(self):
        """Test inicialización del generador."""
        generator = YAMLGenerator()
        assert len(generator.supported_themes) == 4
        assert "classic" in generator.supported_themes
        assert "sb2nov" in generator.supported_themes
        assert "moderncv" in generator.supported_themes
        assert "engineeringresumes" in generator.supported_themes

    def test_supported_languages(self):
        """Test idiomas soportados."""
        generator = YAMLGenerator()
        assert len(generator.supported_languages) == 4
        assert "en" in generator.supported_languages
        assert "es" in generator.supported_languages
        assert "pt" in generator.supported_languages
        assert "fr" in generator.supported_languages


class TestYAMLGeneratorGenerate:
    """Tests para el método generate."""

    @pytest.fixture
    def sample_cv_data(self):
        """CVData de ejemplo."""
        return CVData(
            raw_text="Sample CV text",
            sections={"experience": "detected"},
            metadata={"format": "text"}
        )

    @pytest.fixture
    def sample_contact(self):
        """ContactInfo de ejemplo."""
        return ContactInfo(
            name="John Doe",
            email="john@example.com",
            location="New York, USA",
            linkedin="johndoe"
        )

    def test_generate_minimal_cv(self, sample_cv_data, sample_contact):
        """Test generación de CV mínimo."""
        generator = YAMLGenerator()
        yaml_str = generator.generate(
            cv_data=sample_cv_data,
            contact_info=sample_contact
        )

        # Verificar que se generó algo
        assert yaml_str
        assert len(yaml_str) > 0

        # Verificar que contiene el comentario del schema
        assert "yaml-language-server" in yaml_str
        assert "schema.json" in yaml_str

        # Parsear y verificar estructura
        parsed = yaml.safe_load(yaml_str)
        assert "cv" in parsed
        assert parsed["cv"]["name"] == "John Doe"
        assert parsed["cv"]["email"] == "john@example.com"

    def test_generate_with_all_fields(self, sample_cv_data):
        """Test generación con todos los campos."""
        contact = ContactInfo(
            name="Jane Smith",
            email="jane@example.com",
            phone="+1234567890",
            location="San Francisco, CA",
            website="https://janesmith.com",
            linkedin="janesmith",
            github="janesmith"
        )

        experience = [
            ExperienceEntry(
                company="Tech Corp",
                position="Senior Engineer",
                start_date="2020-01",
                end_date="present",
                location="Remote",
                highlights=["Built feature A", "Led team B"]
            )
        ]

        education = [
            EducationEntry(
                institution="Stanford",
                degree="MS",
                area="Computer Science",
                start_date="2018",
                end_date="2020",
                location="Stanford, CA"
            )
        ]

        skills = [
            SkillEntry(label="Languages", details="Python, Go, Rust"),
            SkillEntry(label="Frameworks", details="Django, FastAPI")
        ]

        summary = "Experienced software engineer with 10+ years"

        generator = YAMLGenerator()
        yaml_str = generator.generate(
            cv_data=sample_cv_data,
            contact_info=contact,
            experience=experience,
            education=education,
            skills=skills,
            summary=summary
        )

        parsed = yaml.safe_load(yaml_str)

        # Verificar información de contacto
        assert parsed["cv"]["name"] == "Jane Smith"
        assert parsed["cv"]["email"] == "jane@example.com"
        assert parsed["cv"]["phone"] == "+1234567890"
        assert parsed["cv"]["website"] == "https://janesmith.com"

        # Verificar redes sociales
        assert "social_networks" in parsed["cv"]
        assert len(parsed["cv"]["social_networks"]) == 2

        # Verificar secciones
        sections = parsed["cv"]["sections"]
        assert "summary" in sections
        assert "experience" in sections
        assert "education" in sections
        assert "skills" in sections

        # Verificar contenido de experiencia
        assert len(sections["experience"]) == 1
        assert sections["experience"][0]["company"] == "Tech Corp"
        assert sections["experience"][0]["position"] == "Senior Engineer"

        # Verificar contenido de educación
        assert len(sections["education"]) == 1
        assert sections["education"][0]["institution"] == "Stanford"

        # Verificar habilidades
        assert len(sections["skills"]) == 2

    def test_generate_with_different_themes(self, sample_cv_data, sample_contact):
        """Test generación con diferentes temas."""
        generator = YAMLGenerator()

        for theme in ["classic", "sb2nov", "moderncv", "engineeringresumes"]:
            yaml_str = generator.generate(
                cv_data=sample_cv_data,
                contact_info=sample_contact,
                theme=theme
            )

            parsed = yaml.safe_load(yaml_str)
            assert parsed["design"]["theme"] == theme

    def test_generate_with_different_languages(self, sample_cv_data, sample_contact):
        """Test generación con diferentes idiomas."""
        generator = YAMLGenerator()

        experience = [
            ExperienceEntry(
                company="Company",
                position="Position",
                start_date="2020",
                end_date="2023"
            )
        ]

        # Test español
        yaml_es = generator.generate(
            cv_data=sample_cv_data,
            contact_info=sample_contact,
            experience=experience,
            language="es"
        )
        parsed_es = yaml.safe_load(yaml_es)
        assert "experiencia" in parsed_es["cv"]["sections"]
        assert parsed_es["locale"]["language"] == "spanish"  # RenderCV v2.3+ usa nombres completos


        # Test inglés
        yaml_en = generator.generate(
            cv_data=sample_cv_data,
            contact_info=sample_contact,
            experience=experience,
            language="en"
        )
        parsed_en = yaml.safe_load(yaml_en)
        assert "experience" in parsed_en["cv"]["sections"]
        assert parsed_en["locale"]["language"] == "english"  # RenderCV v2.3+ usa nombres completos


        # Test portugués
        yaml_pt = generator.generate(
            cv_data=sample_cv_data,
            contact_info=sample_contact,
            experience=experience,
            language="pt"
        )
        parsed_pt = yaml.safe_load(yaml_pt)
        assert "experiência" in parsed_pt["cv"]["sections"]
        assert parsed_pt["locale"]["language"] == "portuguese"  # RenderCV v2.3+ usa nombres completos


        # Test francés
        yaml_fr = generator.generate(
            cv_data=sample_cv_data,
            contact_info=sample_contact,
            experience=experience,
            language="fr"
        )
        parsed_fr = yaml.safe_load(yaml_fr)
        assert "expérience" in parsed_fr["cv"]["sections"]
        assert parsed_fr["locale"]["language"] == "french"  # RenderCV v2.3+ usa nombres completos


    def test_generate_invalid_theme_raises_error(self, sample_cv_data, sample_contact):
        """Test que tema inválido lanza error."""
        generator = YAMLGenerator()

        with pytest.raises(YAMLGeneratorError, match="Tema no soportado"):
            generator.generate(
                cv_data=sample_cv_data,
                contact_info=sample_contact,
                theme="invalid_theme"
            )

    def test_generate_invalid_language_raises_error(self, sample_cv_data, sample_contact):
        """Test que idioma inválido lanza error."""
        generator = YAMLGenerator()

        with pytest.raises(YAMLGeneratorError, match="Idioma no soportado"):
            generator.generate(
                cv_data=sample_cv_data,
                contact_info=sample_contact,
                language="invalid_lang"
            )

    def test_generate_without_contact_uses_default(self, sample_cv_data):
        """Test generación sin ContactInfo usa valores por defecto."""
        generator = YAMLGenerator()
        yaml_str = generator.generate(cv_data=sample_cv_data)

        parsed = yaml.safe_load(yaml_str)
        assert parsed["cv"]["name"] == "Your Name"

    def test_generate_includes_settings(self, sample_cv_data, sample_contact):
        """Test que NO incluye sección de settings (obsoleta en RenderCV v2)."""
        generator = YAMLGenerator()
        yaml_str = generator.generate(
            cv_data=sample_cv_data,
            contact_info=sample_contact
        )

        parsed = yaml.safe_load(yaml_str)
        assert "settings" not in parsed

    def test_generate_with_multiple_experiences(self, sample_cv_data, sample_contact):
        """Test generación con múltiples experiencias."""
        experience = [
            ExperienceEntry(
                company="Company A",
                position="Senior Dev",
                start_date="2020-01",
                end_date="2023-12"
            ),
            ExperienceEntry(
                company="Company B",
                position="Junior Dev",
                start_date="2018-01",
                end_date="2019-12"
            ),
            ExperienceEntry(
                company="Company C",
                position="Intern",
                start_date="2017-06",
                end_date="2017-12"
            )
        ]

        generator = YAMLGenerator()
        yaml_str = generator.generate(
            cv_data=sample_cv_data,
            contact_info=sample_contact,
            experience=experience
        )

        parsed = yaml.safe_load(yaml_str)
        assert len(parsed["cv"]["sections"]["experience"]) == 3

    def test_generate_preserves_special_characters(self, sample_cv_data):
        """Test que preserva caracteres especiales."""
        contact = ContactInfo(
            name="José García",
            location="São Paulo, Brasil"
        )

        summary = "Résumé professionnel avec des accents: é, ñ, ç"

        generator = YAMLGenerator()
        yaml_str = generator.generate(
            cv_data=sample_cv_data,
            contact_info=contact,
            summary=summary
        )

        parsed = yaml.safe_load(yaml_str)
        assert "José" in parsed["cv"]["name"]
        assert "São Paulo" in parsed["cv"]["location"]
        assert "Résumé" in parsed["cv"]["sections"]["summary"][0]


class TestYAMLGeneratorValidation:
    """Tests para el método validate_yaml."""

    def test_validate_valid_yaml(self):
        """Test validación de YAML válido."""
        generator = YAMLGenerator()
        valid_yaml = """
cv:
  name: John Doe
  email: john@example.com
design:
  theme: classic
"""
        assert generator.validate_yaml(valid_yaml) is True

    def test_validate_empty_yaml_raises_error(self):
        """Test que YAML vacío lanza error."""
        generator = YAMLGenerator()

        with pytest.raises(YAMLValidationError, match="vacío"):
            generator.validate_yaml("")

    def test_validate_whitespace_yaml_raises_error(self):
        """Test que YAML solo con espacios lanza error."""
        generator = YAMLGenerator()

        with pytest.raises(YAMLValidationError, match="vacío"):
            generator.validate_yaml("   \n\t  ")

    def test_validate_invalid_syntax_raises_error(self):
        """Test que sintaxis YAML inválida lanza error."""
        generator = YAMLGenerator()
        # YAML con sintaxis realmente inválida (tabs y espacios mezclados incorrectamente)
        invalid_yaml = """
cv:
\tname: John Doe
  \temail: bad@indent.com
    \t  broken: [unclosed
"""
        with pytest.raises(YAMLValidationError, match="sintaxis YAML"):
            generator.validate_yaml(invalid_yaml)

    def test_validate_yaml_without_cv_section_raises_error(self):
        """Test que YAML sin sección 'cv' lanza error."""
        generator = YAMLGenerator()
        yaml_without_cv = """
design:
  theme: classic
settings:
  date: 2025-01-25
"""
        with pytest.raises(YAMLValidationError, match="contener la clave 'cv'"):
            generator.validate_yaml(yaml_without_cv)

    def test_validate_yaml_with_cv_not_dict_raises_error(self):
        """Test que 'cv' no dict lanza error."""
        generator = YAMLGenerator()
        invalid_yaml = """
cv: "This should be a dict"
"""
        with pytest.raises(YAMLValidationError, match="'cv' debe ser un diccionario"):
            generator.validate_yaml(invalid_yaml)

    def test_validate_yaml_without_name_raises_error(self):
        """Test que YAML sin 'name' lanza error."""
        generator = YAMLGenerator()
        yaml_without_name = """
cv:
  email: john@example.com
"""
        with pytest.raises(YAMLValidationError, match="'cv' debe contener 'name'"):
            generator.validate_yaml(yaml_without_name)

    def test_validate_generated_yaml(self):
        """Test que YAML generado pasa validación."""
        generator = YAMLGenerator()
        cv_data = CVData(raw_text="test", sections={}, metadata={})
        contact = ContactInfo(name="Test User")

        yaml_str = generator.generate(cv_data=cv_data, contact_info=contact)

        # Should not raise
        assert generator.validate_yaml(yaml_str) is True


class TestYAMLGeneratorConvenienceMethods:
    """Tests para métodos de conveniencia."""

    def test_generate_from_text(self):
        """Test generate_from_text."""
        generator = YAMLGenerator()
        yaml_str = generator.generate_from_text(
            name="John Doe",
            cv_text="Software Engineer with 5 years experience",
            theme="classic",
            language="en"
        )

        parsed = yaml.safe_load(yaml_str)
        assert parsed["cv"]["name"] == "John Doe"
        assert parsed["design"]["theme"] == "classic"

    def test_parse_and_generate_minimal(self):
        """Test parse_and_generate con datos mínimos."""
        generator = YAMLGenerator()
        structured_data = {
            "name": "Jane Smith"
        }

        yaml_str = generator.parse_and_generate(structured_data)

        parsed = yaml.safe_load(yaml_str)
        assert parsed["cv"]["name"] == "Jane Smith"

    def test_parse_and_generate_with_all_sections(self):
        """Test parse_and_generate con todas las secciones."""
        generator = YAMLGenerator()
        structured_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "location": "New York",
            "linkedin": "johndoe",
            "github": "johndoe",
            "summary": "Experienced engineer",
            "experience": [
                {
                    "company": "Tech Corp",
                    "position": "Engineer",
                    "start_date": "2020-01",
                    "end_date": "2023-12",
                    "highlights": ["Built X", "Led Y"]
                }
            ],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "BS",
                    "area": "CS",
                    "start_date": "2016",
                    "end_date": "2020"
                }
            ],
            "skills": [
                {"label": "Programming", "details": "Python, Go"}
            ]
        }

        yaml_str = generator.parse_and_generate(
            structured_data,
            theme="sb2nov",
            language="es"
        )

        parsed = yaml.safe_load(yaml_str)
        assert parsed["cv"]["name"] == "John Doe"
        assert parsed["cv"]["email"] == "john@example.com"
        assert "experiencia" in parsed["cv"]["sections"]
        assert "educación" in parsed["cv"]["sections"]
        assert "habilidades" in parsed["cv"]["sections"]
        assert parsed["design"]["theme"] == "sb2nov"

    def test_parse_and_generate_without_name_raises_error(self):
        """Test parse_and_generate sin nombre lanza error."""
        generator = YAMLGenerator()
        structured_data = {
            "email": "test@example.com"
        }

        with pytest.raises(YAMLGeneratorError, match="'name' es requerido"):
            generator.parse_and_generate(structured_data)


class TestYAMLGeneratorEdgeCases:
    """Tests para casos extremos."""

    def test_generate_with_empty_lists(self):
        """Test generación con listas vacías."""
        generator = YAMLGenerator()
        cv_data = CVData(raw_text="test", sections={}, metadata={})
        contact = ContactInfo(name="Test User")

        yaml_str = generator.generate(
            cv_data=cv_data,
            contact_info=contact,
            experience=[],
            education=[],
            skills=[]
        )

        parsed = yaml.safe_load(yaml_str)
        # Las secciones vacías no deberían agregarse
        assert parsed["cv"]["name"] == "Test User"

    def test_generate_with_none_optional_fields(self):
        """Test generación con campos opcionales None."""
        generator = YAMLGenerator()
        cv_data = CVData(raw_text="test", sections={}, metadata={})
        contact = ContactInfo(name="Test User")

        # Esto no debería fallar
        yaml_str = generator.generate(
            cv_data=cv_data,
            contact_info=contact,
            experience=None,
            education=None,
            skills=None,
            summary=None
        )

        assert yaml_str
        parsed = yaml.safe_load(yaml_str)
        assert parsed["cv"]["name"] == "Test User"

    def test_generate_with_very_long_text(self):
        """Test generación con texto muy largo."""
        generator = YAMLGenerator()
        cv_data = CVData(raw_text="x" * 10000, sections={}, metadata={})
        contact = ContactInfo(name="Test User")

        long_summary = "A" * 5000

        yaml_str = generator.generate(
            cv_data=cv_data,
            contact_info=contact,
            summary=long_summary
        )

        assert yaml_str
        assert generator.validate_yaml(yaml_str)
