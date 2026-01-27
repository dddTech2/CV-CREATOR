"""
Tests para el sistema centralizado de prompts.
"""
import pytest
from src.prompts import PromptManager


def test_get_job_analysis_prompt():
    """Test que el prompt de análisis de vacante se genera correctamente."""
    description = "Senior Python Developer needed."
    prompt = PromptManager.get_job_analysis_prompt(description)
    
    assert description in prompt
    assert "Analiza la siguiente descripción de vacante" in prompt
    assert "technical_skills" in prompt


def test_get_question_generation_prompt():
    """Test que el prompt de generación de preguntas se genera correctamente."""
    gaps = "Missing Docker"
    cv = "Has Python"
    job = "Needs Docker"
    
    prompt = PromptManager.get_question_generation_prompt(
        gaps_summary=gaps,
        cv_summary=cv,
        job_summary=job,
        max_questions=3,
        language="en español"
    )
    
    assert gaps in prompt
    assert cv in prompt
    assert job in prompt
    assert "en español" in prompt
    assert "Genera 3 preguntas" in prompt


def test_get_experience_rewrite_prompt():
    """Test que el prompt de reescritura de experiencia se genera correctamente."""
    prompt = PromptManager.get_experience_rewrite_prompt(
        title="Dev",
        company="Corp",
        original_description="Did stuff",
        skills_to_add=["Docker"],
        job_keywords=["Python"],
        language="en español"
    )
    
    assert "Dev" in prompt
    assert "Corp" in prompt
    assert "Did stuff" in prompt
    assert "Docker" in prompt
    assert "Python" in prompt
    assert "en español" in prompt


def test_get_data_structuring_prompt():
    """Test que el prompt de estructuración de datos se genera correctamente."""
    cv_text = "John Doe\nDeveloper"
    prompt = PromptManager.get_data_structuring_prompt(cv_text)
    
    assert cv_text in prompt
    assert "JSON Schema requerido" in prompt
    assert "education" in prompt
