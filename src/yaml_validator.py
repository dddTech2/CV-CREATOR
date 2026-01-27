"""
Validador de YAML contra schema de RenderCV.

Valida que los archivos YAML generados cumplan con el schema oficial de RenderCV.
"""
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft7Validator, validate
from jsonschema import ValidationError as JSONSchemaValidationError


class ValidationSeverity(Enum):
    """Severidad de un error de validación."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Representa un problema de validación."""
    message: str
    severity: ValidationSeverity
    path: str | None = None
    schema_path: str | None = None

    def __str__(self) -> str:
        """Representación en string del issue."""
        parts = [f"[{self.severity.value.upper()}]"]
        if self.path:
            parts.append(f"at {self.path}:")
        parts.append(self.message)
        return " ".join(parts)


@dataclass
class ValidationResult:
    """Resultado de una validación de YAML."""
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    yaml_data: dict[str, Any] | None = None

    @property
    def errors(self) -> list[ValidationIssue]:
        """Retorna solo los errores."""
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Retorna solo los warnings."""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def error_count(self) -> int:
        """Cuenta de errores."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Cuenta de warnings."""
        return len(self.warnings)

    def get_summary(self) -> str:
        """Obtiene un resumen de la validación."""
        if self.is_valid:
            summary = "✅ YAML válido"
            if self.warning_count > 0:
                summary += f" (con {self.warning_count} warning(s))"
            return summary
        else:
            return f"❌ YAML inválido: {self.error_count} error(es), {self.warning_count} warning(s)"


class YAMLValidatorError(Exception):
    """Excepción base para errores del validador."""
    pass


class SchemaNotFoundError(YAMLValidatorError):
    """Excepción cuando no se encuentra el schema."""
    pass


class YAMLValidator:
    """
    Validador de YAML contra schema de RenderCV.

    Valida que los archivos YAML cumplan con el schema oficial de RenderCV
    usando jsonschema.
    """

    DEFAULT_SCHEMA_PATH = "schemas/rendercv_schema.json"

    def __init__(self, schema_path: str | None = None):
        """
        Inicializa el validador.

        Args:
            schema_path: Ruta al schema JSON de RenderCV. Si es None, usa el schema por defecto.

        Raises:
            SchemaNotFoundError: Si el schema no se encuentra
        """
        self.schema_path = schema_path or self.DEFAULT_SCHEMA_PATH
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)

    def _load_schema(self) -> dict[str, Any]:
        """
        Carga el schema JSON de RenderCV.

        Returns:
            Diccionario con el schema

        Raises:
            SchemaNotFoundError: Si el schema no existe
        """
        schema_file = Path(self.schema_path)

        if not schema_file.exists():
            raise SchemaNotFoundError(
                f"Schema no encontrado: {self.schema_path}. "
                "Asegúrate de haber descargado el schema de RenderCV."
            )

        try:
            with open(schema_file, encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise YAMLValidatorError(f"Error al parsear schema JSON: {e}")
        except Exception as e:
            raise YAMLValidatorError(f"Error al cargar schema: {e}")

    def validate(self, yaml_content: str) -> ValidationResult:
        """
        Valida un YAML contra el schema de RenderCV.

        Args:
            yaml_content: String con el contenido YAML

        Returns:
            ValidationResult con el resultado de la validación
        """
        issues: list[ValidationIssue] = []

        # 1. Parsear YAML
        try:
            yaml_data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            issues.append(ValidationIssue(
                message=f"Error de sintaxis YAML: {str(e)}",
                severity=ValidationSeverity.ERROR,
                path=None
            ))
            return ValidationResult(is_valid=False, issues=issues)

        # 2. Verificar que no sea None
        if yaml_data is None:
            issues.append(ValidationIssue(
                message="YAML vacío o sin contenido",
                severity=ValidationSeverity.ERROR
            ))
            return ValidationResult(is_valid=False, issues=issues)

        # 3. Validar contra schema
        try:
            validate(instance=yaml_data, schema=self.schema)
            
            # Validación semántica adicional (reglas de negocio de RenderCV)
            semantic_issues = self._validate_semantic_rules(yaml_data)
            issues.extend(semantic_issues)
            
            # Si hay errores semánticos, el resultado es inválido
            if any(i.severity == ValidationSeverity.ERROR for i in semantic_issues):
                return ValidationResult(
                    is_valid=False,
                    issues=issues,
                    yaml_data=yaml_data
                )

            # Si llega aquí, la validación fue exitosa
            return ValidationResult(
                is_valid=True,
                issues=issues,
                yaml_data=yaml_data
            )
        except JSONSchemaValidationError as e:
            # Convertir error de jsonschema a ValidationIssue
            issue = self._convert_jsonschema_error(e)
            issues.append(issue)

            # Recolectar todos los errores de validación
            for error in self.validator.iter_errors(yaml_data):
                if error != e:  # Evitar duplicado
                    issues.append(self._convert_jsonschema_error(error))

            return ValidationResult(
                is_valid=False,
                issues=issues,
                yaml_data=yaml_data
            )

    def _validate_semantic_rules(self, yaml_data: dict[str, Any]) -> list[ValidationIssue]:
        """
        Valida reglas semánticas que el schema JSON no cubre.
        
        Args:
            yaml_data: Datos YAML parseados
            
        Returns:
            Lista de issues encontrados
        """
        issues: list[ValidationIssue] = []
        
        if "cv" in yaml_data and isinstance(yaml_data["cv"], dict):
            cv = yaml_data["cv"]
            
            # Validar teléfono (RenderCV v2.3+ requiere formato estricto sin espacios ni guiones)
            if "phone" in cv and cv["phone"]:
                phone = cv["phone"]
                # Phone puede ser string o lista
                if isinstance(phone, str):
                    phone_str = phone.strip()
                    if not phone_str.startswith("+"):
                        issues.append(ValidationIssue(
                            message=f"El teléfono '{phone}' debe empezar con '+' seguido del código de país (ej: +12345678900). RenderCV fallará sin esto.",
                            severity=ValidationSeverity.ERROR,
                            path="cv.phone"
                        ))
                    elif " " in phone_str or "-" in phone_str or "(" in phone_str:
                        issues.append(ValidationIssue(
                            message=f"El teléfono '{phone}' contiene espacios o guiones. RenderCV v2.3+ requiere formato compacto (ej: +12345678900 sin espacios ni guiones).",
                            severity=ValidationSeverity.WARNING,
                            path="cv.phone"
                        ))
                elif isinstance(phone, list):
                    for idx, p in enumerate(phone):
                        if isinstance(p, str):
                            p_str = p.strip()
                            if not p_str.startswith("+"):
                                issues.append(ValidationIssue(
                                    message=f"El teléfono '{p}' debe empezar con '+' seguido del código de país.",
                                    severity=ValidationSeverity.ERROR,
                                    path=f"cv.phone[{idx}]"
                                ))
                            elif " " in p_str or "-" in p_str or "(" in p_str:
                                issues.append(ValidationIssue(
                                    message=f"El teléfono '{p}' contiene espacios o guiones. Use formato compacto.",
                                    severity=ValidationSeverity.WARNING,
                                    path=f"cv.phone[{idx}]"
                                ))

        return issues

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        Valida un archivo YAML.

        Args:
            file_path: Ruta al archivo YAML

        Returns:
            ValidationResult con el resultado

        Raises:
            YAMLValidatorError: Si hay error al leer el archivo
        """
        try:
            with open(file_path, encoding='utf-8') as f:
                yaml_content = f.read()
            return self.validate(yaml_content)
        except FileNotFoundError:
            raise YAMLValidatorError(f"Archivo no encontrado: {file_path}")
        except Exception as e:
            raise YAMLValidatorError(f"Error al leer archivo: {e}")

    def _convert_jsonschema_error(self, error: JSONSchemaValidationError) -> ValidationIssue:
        """
        Convierte un error de jsonschema a ValidationIssue.

        Args:
            error: Error de jsonschema

        Returns:
            ValidationIssue correspondiente
        """
        # Construir path legible
        path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"

        # Construir mensaje
        message = error.message

        # Agregar contexto si está disponible
        if error.validator:
            message = f"{error.validator} validation failed: {message}"

        return ValidationIssue(
            message=message,
            severity=ValidationSeverity.ERROR,
            path=path,
            schema_path=".".join(str(p) for p in error.absolute_schema_path) if error.absolute_schema_path else None
        )

    def check_required_fields(self, yaml_data: dict[str, Any]) -> list[ValidationIssue]:
        """
        Verifica que los campos requeridos estén presentes.

        Args:
            yaml_data: Datos YAML parseados

        Returns:
            Lista de issues encontrados
        """
        issues: list[ValidationIssue] = []

        # Verificar estructura básica
        if "cv" not in yaml_data:
            issues.append(ValidationIssue(
                message="Falta la sección 'cv' requerida",
                severity=ValidationSeverity.ERROR,
                path="root"
            ))
            return issues

        cv_section = yaml_data["cv"]

        # Verificar campos requeridos en cv
        if "name" not in cv_section:
            issues.append(ValidationIssue(
                message="Falta el campo 'name' requerido en la sección 'cv'",
                severity=ValidationSeverity.ERROR,
                path="cv"
            ))

        return issues

    def validate_with_suggestions(self, yaml_content: str) -> ValidationResult:
        """
        Valida YAML y proporciona sugerencias de corrección.

        Args:
            yaml_content: Contenido YAML

        Returns:
            ValidationResult con sugerencias adicionales
        """
        result = self.validate(yaml_content)

        # Agregar sugerencias basadas en errores comunes
        if not result.is_valid and result.yaml_data:
            suggestions = self._generate_suggestions(result.yaml_data, result.errors)
            for suggestion in suggestions:
                result.issues.append(suggestion)

        return result

    def _generate_suggestions(
        self,
        yaml_data: dict[str, Any],
        errors: list[ValidationIssue]
    ) -> list[ValidationIssue]:
        """
        Genera sugerencias basadas en errores.

        Args:
            yaml_data: Datos YAML
            errors: Errores encontrados

        Returns:
            Lista de sugerencias como ValidationIssues de tipo INFO
        """
        suggestions: list[ValidationIssue] = []

        # Sugerencias basadas en errores comunes
        for error in errors:
            if error.path and "name" in error.message.lower():
                suggestions.append(ValidationIssue(
                    message="Asegúrate de que el campo 'name' sea una string no vacía",
                    severity=ValidationSeverity.INFO,
                    path=error.path
                ))

            if "date" in error.message.lower():
                suggestions.append(ValidationIssue(
                    message="Las fechas deben estar en formato YYYY-MM-DD o YYYY-MM o YYYY",
                    severity=ValidationSeverity.INFO,
                    path=error.path
                ))

        return suggestions
