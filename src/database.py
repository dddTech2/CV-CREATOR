"""
Gestor de base de datos Supabase PostgreSQL para el historial de CVs generados.
"""

import os
from datetime import datetime, timezone
from typing import Any, cast

from src.logger import get_logger
from supabase import Client, create_client

logger = get_logger(__name__)


class CVDatabase:
    """Cliente de base de datos que conecta a Supabase PostgreSQL.

    El esquema se gestiona mediante migraciones SQL en ``supabase/migrations/``.
    Cada método acepta un ``user_id`` opcional para soporte multiusuario;
    mientras no se implemente autenticación, se pasa ``None``.
    """

    _client: Client | None = None

    def __init__(self) -> None:
        if CVDatabase._client is None:
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_KEY", "")
            if not url or not key:
                raise ValueError(
                    "Las variables de entorno SUPABASE_URL y SUPABASE_KEY "
                    "son requeridas. Configúralas en .env o en Streamlit secrets."
                )
            CVDatabase._client = create_client(url, key)
            logger.info("Cliente Supabase inicializado")
        self.client: Client = CVDatabase._client

    @staticmethod
    def _rows(response: Any) -> list[dict[str, Any]]:
        """Cast Supabase response data to a typed list for mypy."""
        return cast(list[dict[str, Any]], response.data)

    # ------------------------------------------------------------------
    # cv_history
    # ------------------------------------------------------------------

    def save_cv(
        self,
        job_title: str,
        yaml_content: str,
        company: str | None = None,
        language: str = "es",
        theme: str = "classic",
        yaml_path: str | None = None,
        pdf_path: str | None = None,
        original_cv: str | None = None,
        job_description: str | None = None,
        gap_analysis: str | None = None,
        questions_asked: str | None = None,
        user_id: str | None = None,
    ) -> int:
        """Guarda un CV generado en la base de datos.

        Args:
            job_title: Título de la vacante.
            yaml_content: Contenido YAML generado.
            company: Nombre de la empresa (opcional).
            language: Idioma del CV.
            theme: Tema de RenderCV usado.
            yaml_path: Ruta del archivo YAML guardado.
            pdf_path: Ruta del PDF generado.
            original_cv: CV original del usuario (opcional).
            job_description: Descripción de la vacante (opcional).
            gap_analysis: Resultado del análisis de brechas.
            questions_asked: Preguntas hechas al usuario.
            user_id: UUID del usuario autenticado (opcional).

        Returns:
            ID del registro creado.
        """
        try:
            data: dict = {
                "job_title": job_title,
                "company": company,
                "language": language,
                "theme": theme,
                "yaml_content": yaml_content,
                "yaml_path": yaml_path,
                "pdf_path": pdf_path,
                "original_cv": original_cv,
                "job_description": job_description,
                "gap_analysis": gap_analysis,
                "questions_asked": questions_asked,
            }
            if user_id is not None:
                data["user_id"] = user_id

            response = self.client.table("cv_history").insert(data).execute()
            rows = self._rows(response)
            cv_id: int = rows[0]["id"]
            logger.info(f"CV guardado con ID: {cv_id} ({job_title})")
            return cv_id
        except Exception as e:
            logger.error(f"Error guardando CV en DB: {e}", exc_info=True)
            raise

    def get_all_cvs(self, user_id: str | None = None) -> list[dict]:
        """Obtiene todos los CVs guardados, ordenados por fecha descendente.

        Args:
            user_id: Filtrar por usuario (opcional).

        Returns:
            Lista de diccionarios con los datos de cada CV.
        """
        query = self.client.table("cv_history").select(
            "id, created_at, job_title, company, language, theme, yaml_path, pdf_path"
        )
        if user_id is not None:
            query = query.eq("user_id", user_id)
        response = query.order("created_at", desc=True).execute()
        return self._rows(response)

    def get_cv_by_id(self, cv_id: int, user_id: str | None = None) -> dict | None:
        """Obtiene un CV específico por su ID.

        Args:
            cv_id: ID del CV.
            user_id: Filtrar por usuario (opcional).

        Returns:
            Diccionario con todos los datos del CV o ``None`` si no existe.
        """
        query = self.client.table("cv_history").select("*").eq("id", cv_id)
        if user_id is not None:
            query = query.eq("user_id", user_id)
        response = query.execute()
        rows = self._rows(response)
        return rows[0] if rows else None

    def delete_cv(self, cv_id: int, user_id: str | None = None) -> bool:
        """Elimina un CV del historial.

        Args:
            cv_id: ID del CV a eliminar.
            user_id: Filtrar por usuario (opcional).

        Returns:
            ``True`` si se eliminó correctamente, ``False`` si no existía.
        """
        query = self.client.table("cv_history").delete().eq("id", cv_id)
        if user_id is not None:
            query = query.eq("user_id", user_id)
        response = query.execute()
        return len(self._rows(response)) > 0

    def clear_all(self, user_id: str | None = None) -> int:
        """Elimina todos los CVs del historial.

        Args:
            user_id: Si se proporciona, solo elimina los del usuario.

        Returns:
            Número de registros eliminados.
        """
        query = self.client.table("cv_history").delete()
        if user_id is not None:  # noqa: SIM108
            query = query.eq("user_id", user_id)
        else:
            # Supabase requiere al menos un filtro en DELETE.
            query = query.gte("id", 0)
        response = query.execute()
        return len(self._rows(response))

    # ------------------------------------------------------------------
    # skill_memory
    # ------------------------------------------------------------------

    def save_skill_answer(
        self,
        skill_name: str,
        answer_text: str,
        user_id: str | None = None,
    ) -> None:
        """Guarda o actualiza una respuesta de habilidad en la memoria.

        Si la habilidad ya existe para el usuario, actualiza el texto e
        incrementa ``usage_count``.

        Args:
            skill_name: Nombre de la habilidad (se normaliza a minúsculas).
            answer_text: Texto de la respuesta.
            user_id: UUID del usuario (opcional).
        """
        try:
            normalized_skill = skill_name.strip().lower()
            now = datetime.now(timezone.utc).isoformat()  # noqa: UP017

            # Buscar registro existente para incrementar usage_count.
            existing_query = (
                self.client.table("skill_memory")
                .select("usage_count")
                .eq("skill_name", normalized_skill)
            )
            if user_id is not None:
                existing_query = existing_query.eq("user_id", user_id)
            else:
                existing_query = existing_query.is_("user_id", "null")
            existing = existing_query.execute()

            existing_rows = self._rows(existing)
            usage_count = existing_rows[0]["usage_count"] + 1 if existing_rows else 1

            data: dict = {
                "skill_name": normalized_skill,
                "answer_text": answer_text,
                "updated_at": now,
                "usage_count": usage_count,
            }
            if user_id is not None:
                data["user_id"] = user_id

            self.client.table("skill_memory").upsert(
                data, on_conflict="user_id,skill_name"
            ).execute()
            logger.info(f"Respuesta guardada para skill: {normalized_skill}")
        except Exception as e:
            logger.error(f"Error guardando skill answer: {e}", exc_info=True)

    def get_skill_answer(self, skill_name: str, user_id: str | None = None) -> str | None:
        """Recupera una respuesta previa para una habilidad.

        Args:
            skill_name: Nombre de la habilidad.
            user_id: UUID del usuario (opcional).

        Returns:
            Texto de la respuesta o ``None`` si no existe.
        """
        try:
            normalized_skill = skill_name.strip().lower()
            query = (
                self.client.table("skill_memory")
                .select("answer_text")
                .eq("skill_name", normalized_skill)
            )
            if user_id is not None:
                query = query.eq("user_id", user_id)
            response = query.execute()
            rows = self._rows(response)
            return rows[0]["answer_text"] if rows else None
        except Exception as e:
            logger.error(f"Error recuperando skill answer: {e}", exc_info=True)
            return None

    def get_all_skill_answers(self, user_id: str | None = None) -> dict[str, str]:
        """Recupera todas las respuestas de habilidades almacenadas.

        Args:
            user_id: UUID del usuario (opcional).

        Returns:
            Diccionario ``{skill_name: answer_text}``.
        """
        try:
            query = self.client.table("skill_memory").select("skill_name, answer_text")
            if user_id is not None:
                query = query.eq("user_id", user_id)
            response = query.execute()
            return {row["skill_name"]: row["answer_text"] for row in self._rows(response)}
        except Exception as e:
            logger.error(
                f"Error recuperando todas las skill answers: {e}",
                exc_info=True,
            )
            return {}

    def delete_skill_answer(self, skill_name: str, user_id: str | None = None) -> bool:
        """Elimina una respuesta de habilidad de la memoria.

        Args:
            skill_name: Nombre de la habilidad a eliminar.
            user_id: UUID del usuario (opcional).

        Returns:
            ``True`` si se eliminó, ``False`` si no existía o hubo error.
        """
        try:
            normalized_skill = skill_name.strip().lower()
            query = self.client.table("skill_memory").delete().eq("skill_name", normalized_skill)
            if user_id is not None:
                query = query.eq("user_id", user_id)
            response = query.execute()
            logger.info(f"Skill eliminada de memoria: {normalized_skill}")
            return len(self._rows(response)) > 0
        except Exception as e:
            logger.error(f"Error eliminando skill answer: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # base_cv
    # ------------------------------------------------------------------

    def save_base_cv(self, cv_text: str, user_id: str | None = None) -> None:
        """Guarda o actualiza el CV base predeterminado (uno por usuario).

        Args:
            cv_text: El texto del CV a guardar como base.
            user_id: UUID del usuario (opcional).
        """
        try:
            now = datetime.now(timezone.utc).isoformat()  # noqa: UP017
            data: dict = {
                "cv_text": cv_text,
                "updated_at": now,
            }
            if user_id is not None:
                data["user_id"] = user_id

            self.client.table("base_cv").upsert(data, on_conflict="user_id").execute()
            logger.info("CV Base guardado exitosamente")
        except Exception as e:
            logger.error(f"Error guardando CV Base: {e}", exc_info=True)
            raise

    def get_base_cv(self, user_id: str | None = None) -> str | None:
        """Recupera el CV base predeterminado si existe.

        Args:
            user_id: UUID del usuario (opcional).

        Returns:
            Texto del CV base o ``None``.
        """
        try:
            query = self.client.table("base_cv").select("cv_text")
            if user_id is not None:
                query = query.eq("user_id", user_id)
            response = query.limit(1).execute()
            rows = self._rows(response)
            return rows[0]["cv_text"] if rows else None
        except Exception as e:
            logger.error(f"Error recuperando CV Base: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # interview_sessions
    # ------------------------------------------------------------------

    def save_interview_session(
        self,
        cv_id: int | None,
        question: str,
        answer: str,
        user_id: str | None = None,
    ) -> int:
        """Guarda una sesión de pregunta/respuesta de entrevista.

        Args:
            cv_id: ID del CV asociado (puede ser ``None`` si es sesión libre).
            question: Pregunta realizada.
            answer: Respuesta generada.
            user_id: UUID del usuario (opcional).

        Returns:
            ID del registro creado.
        """
        try:
            data: dict = {
                "cv_id": cv_id,
                "question": question,
                "generated_answer": answer,
            }
            if user_id is not None:
                data["user_id"] = user_id

            response = self.client.table("interview_sessions").insert(data).execute()
            rows = self._rows(response)
            session_id: int = rows[0]["id"]
            return session_id
        except Exception as e:
            logger.error(f"Error guardando sesión de entrevista: {e}", exc_info=True)
            raise

    def get_interview_sessions(
        self,
        cv_id: int | None = None,
        limit: int = 50,
        user_id: str | None = None,
    ) -> list[dict]:
        """Recupera historial de entrevistas.

        Args:
            cv_id: Filtrar por ID de CV (opcional).
            limit: Límite de resultados.
            user_id: UUID del usuario (opcional).

        Returns:
            Lista de sesiones.
        """
        query = self.client.table("interview_sessions").select("*")
        if cv_id is not None:
            query = query.eq("cv_id", cv_id)
        if user_id is not None:
            query = query.eq("user_id", user_id)
        response = query.order("created_at", desc=True).limit(limit).execute()
        return self._rows(response)
