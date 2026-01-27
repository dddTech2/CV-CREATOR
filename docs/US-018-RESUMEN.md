# US-018: Backend - Sistema de prompts para Gemini

## 📋 Resumen

**User Story:** Como sistema, necesito prompts bien estructurados para cada fase del proceso.

**Estado:** ✅ COMPLETADA

**Fecha:** 25 de enero de 2026

---

## 🎯 Objetivos Completados

✅ **Centralización de Prompts:**
- Creado módulo `src/prompts.py` que contiene todos los templates de prompts del sistema.
- Eliminados prompts hardcodeados en clases individuales (`JobAnalyzer`, `QuestionGenerator`, etc.).

✅ **Gestor de Prompts (`PromptManager`):**
- Clase estática con métodos específicos para construir cada tipo de prompt.
- Validación implícita de variables requeridas mediante argumentos de función.
- Interpolación segura de strings.

✅ **Soporte de Internacionalización:**
- Los prompts soportan el parámetro `language` para adaptar las instrucciones al idioma del usuario.

✅ **Testing:**
- Tests unitarios verificando que cada prompt se genera correctamente con las variables esperadas.

---

## 🏗️ Implementación Técnica

### Estructura de `PromptTemplates`

```python
class PromptTemplates:
    JOB_ANALYSIS = "Analiza la siguiente descripción..."
    QUESTION_GENERATION = "Eres un estratega de carrera..."
    EXPERIENCE_REWRITE = "Eres un experto en redacción..."
    DATA_STRUCTURING = "Extrae la información en formato JSON..."
```

### Uso con `PromptManager`

```python
from src.prompts import PromptManager

# Generar prompt para reescritura
prompt = PromptManager.get_experience_rewrite_prompt(
    title="Developer",
    company="Tech Corp",
    original_description="...",
    skills_to_add=["Docker", "AWS"],
    job_keywords=["Python", "API"],
    language="es"
)
```

### Ventajas de esta Refactorización

1. **Mantenibilidad:** Si queremos cambiar cómo la IA se comporta, solo editamos un archivo.
2. **Testing:** Podemos testear los prompts aisladamente sin llamar a la API.
3. **Seguridad:** Previene errores de typos en nombres de variables interpoladas.
4. **Limpieza:** El código de negocio (`Analyzers`, `Generators`) queda libre de bloques de texto largos.

---

## 🧪 Pruebas Realizadas

- [x] Verificación de generación de prompt de Análisis de Vacante
- [x] Verificación de generación de prompt de Preguntas
- [x] Verificación de generación de prompt de Reescritura
- [x] Verificación de generación de prompt de Estructuración de Datos
- [x] Ejecución de suite completa de tests para asegurar no regresión

---

## 🚀 Próximos Pasos

- **US-019 (Logging):** Implementar sistema de logging robusto.
