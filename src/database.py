"""
Gestor de base de datos SQLite para el historial de CVs generados.
"""
import sqlite3
from pathlib import Path

from src.logger import get_logger

logger = get_logger(__name__)


class CVDatabase:
    _initialized = False

    def __init__(self, db_path: str = "data/cv_history.db"):
        self.db_path = db_path
        if not CVDatabase._initialized:
            self._init_db()
            CVDatabase._initialized = True

    def _init_db(self):
        """Inicializa la base de datos y crea la tabla si no existe."""
        try:
            # Asegurar que el directorio data/ existe
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cv_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    job_title TEXT NOT NULL,
                    company TEXT,
                    language TEXT DEFAULT 'es',
                    theme TEXT DEFAULT 'classic',
                    yaml_content TEXT NOT NULL,
                    yaml_path TEXT,
                    pdf_path TEXT,
                    original_cv TEXT,
                    job_description TEXT,
                    gap_analysis TEXT,
                    questions_asked TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_memory (
                    skill_name TEXT PRIMARY KEY,
                    answer_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 1
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS base_cv (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    cv_text TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interview_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cv_id INTEGER,
                    question TEXT NOT NULL,
                    generated_answer TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(cv_id) REFERENCES cv_history(id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info(f"Base de datos inicializada en {self.db_path}")
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}", exc_info=True)
            raise

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
        questions_asked: str | None = None
    ) -> int:
        """
        Guarda un CV generado en la base de datos.
        
        Args:
            job_title: Título de la vacante
            yaml_content: Contenido YAML generado
            company: Nombre de la empresa (opcional)
            language: Idioma del CV
            theme: Tema de RenderCV usado
            yaml_path: Ruta del archivo YAML guardado
            pdf_path: Ruta del PDF generado
            original_cv: CV original del usuario (opcional)
            job_description: Descripción de la vacante (opcional)
            gap_analysis: Resultado del análisis de brechas
            questions_asked: Preguntas hechas al usuario
            
        Returns:
            ID del registro creado
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO cv_history 
                (job_title, company, language, theme, yaml_content, yaml_path, pdf_path,
                 original_cv, job_description, gap_analysis, questions_asked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_title, company, language, theme, yaml_content, yaml_path, pdf_path,
                  original_cv, job_description, gap_analysis, questions_asked))
            
            cv_id = cursor.lastrowid if cursor.lastrowid is not None else 0
            conn.commit()
            conn.close()
            
            logger.info(f"CV guardado con ID: {cv_id} ({job_title})")
            return cv_id
        except Exception as e:
            logger.error(f"Error guardando CV en DB: {e}", exc_info=True)
            raise

    def get_all_cvs(self) -> list[dict]:
        """
        Obtiene todos los CVs guardados, ordenados por fecha (más recientes primero).
        
        Returns:
            Lista de diccionarios con los datos de cada CV
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, created_at, job_title, company, language, theme, yaml_path, pdf_path
            FROM cv_history
            ORDER BY created_at DESC, id DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_cv_by_id(self, cv_id: int) -> dict | None:
        """
        Obtiene un CV específico por su ID.
        
        Args:
            cv_id: ID del CV
            
        Returns:
            Diccionario con todos los datos del CV o None si no existe
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM cv_history
            WHERE id = ?
        """, (cv_id,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def delete_cv(self, cv_id: int) -> bool:
        """
        Elimina un CV del historial.
        
        Args:
            cv_id: ID del CV a eliminar
            
        Returns:
            True si se eliminó correctamente, False si no existía
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cv_history WHERE id = ?", (cv_id,))
        affected = cursor.rowcount

        conn.commit()
        conn.close()

        return affected > 0

    def clear_all(self) -> int:
        """
        Elimina todos los CVs del historial.
        
        Returns:
            Número de registros eliminados
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cv_history")
        affected = cursor.rowcount

        conn.commit()
        conn.close()

        return affected

    def save_skill_answer(self, skill_name: str, answer_text: str) -> None:
        """
        Guarda o actualiza una respuesta de habilidad en la memoria.
        
        Args:
            skill_name: Nombre de la habilidad (se normalizará a minúsculas)
            answer_text: Texto de la respuesta
        """
        try:
            normalized_skill = skill_name.strip().lower()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Usar UPSERT (INSERT OR REPLACE)
            cursor.execute("""
                INSERT INTO skill_memory (skill_name, answer_text, updated_at, usage_count)
                VALUES (?, ?, CURRENT_TIMESTAMP, 1)
                ON CONFLICT(skill_name) DO UPDATE SET
                    answer_text = excluded.answer_text,
                    updated_at = CURRENT_TIMESTAMP,
                    usage_count = skill_memory.usage_count + 1
            """, (normalized_skill, answer_text))
            
            conn.commit()
            conn.close()
            logger.info(f"Respuesta guardada para skill: {normalized_skill}")
            
        except Exception as e:
            logger.error(f"Error guardando skill answer: {e}", exc_info=True)
            # No lanzar excepción para no interrumpir el flujo principal

    def get_skill_answer(self, skill_name: str) -> str | None:
        """
        Recupera una respuesta previa para una habilidad.
        
        Args:
            skill_name: Nombre de la habilidad
            
        Returns:
            Texto de la respuesta o None si no existe
        """
        try:
            normalized_skill = skill_name.strip().lower()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT answer_text FROM skill_memory WHERE skill_name = ?", (normalized_skill,))
            row = cursor.fetchone()
            
            conn.close()
            
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"Error recuperando skill answer: {e}", exc_info=True)
            return None

    def get_all_skill_answers(self) -> dict[str, str]:
        """
        Recupera todas las respuestas de habilidades almacenadas.
        
        Returns:
            Diccionario {skill_name: answer_text}
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT skill_name, answer_text FROM skill_memory")
            rows = cursor.fetchall()
            
            conn.close()
            
            return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"Error recuperando todas las skill answers: {e}", exc_info=True)
            return {}

    def delete_skill_answer(self, skill_name: str) -> bool:
        """
        Elimina una respuesta de habilidad de la memoria.
        
        Args:
            skill_name: Nombre de la habilidad a eliminar
            
        Returns:
            True si se eliminó, False si no existía o error
        """
        try:
            normalized_skill = skill_name.strip().lower()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM skill_memory WHERE skill_name = ?", (normalized_skill,))
            affected = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            logger.info(f"Skill eliminada de memoria: {normalized_skill}")
            return affected > 0
            
        except Exception as e:
            logger.error(f"Error eliminando skill answer: {e}", exc_info=True)
            return False

    def save_base_cv(self, cv_text: str) -> None:
        """
        Guarda o actualiza el CV base predeterminado (Singleton record).
        
        Args:
            cv_text: El texto del CV a guardar como base.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Usar UPSERT para mantener solo un registro con id=1
            cursor.execute("""
                INSERT INTO base_cv (id, cv_text, updated_at)
                VALUES (1, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    cv_text = excluded.cv_text,
                    updated_at = CURRENT_TIMESTAMP
            """, (cv_text,))
            
            conn.commit()
            conn.close()
            logger.info("CV Base guardado exitosamente")
            
        except Exception as e:
            logger.error(f"Error guardando CV Base: {e}", exc_info=True)
            raise

    def get_base_cv(self) -> str | None:
        """
        Recupera el CV base predeterminado si existe.
        
        Returns:
            Texto del CV base o None.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT cv_text FROM base_cv WHERE id = 1")
            row = cursor.fetchone()
            
            conn.close()
            
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"Error recuperando CV Base: {e}", exc_info=True)
            return None

    def save_interview_session(self, cv_id: int | None, question: str, answer: str) -> int:
        """
        Guarda una sesión de pregunta/respuesta de entrevista.
        
        Args:
            cv_id: ID del CV generado asociado (puede ser None si es sesión libre)
            question: Pregunta realizada
            answer: Respuesta generada
            
        Returns:
            ID del registro creado
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO interview_sessions (cv_id, question, generated_answer)
                VALUES (?, ?, ?)
            """, (cv_id, question, answer))
            
            session_id = cursor.lastrowid if cursor.lastrowid is not None else 0
            conn.commit()
            conn.close()
            
            return session_id
        except Exception as e:
            logger.error(f"Error guardando sesión de entrevista: {e}", exc_info=True)
            raise

    def get_interview_sessions(self, cv_id: int | None = None, limit: int = 50) -> list[dict]:
        """
        Recupera historial de entrevistas.
        
        Args:
            cv_id: Filtrar por ID de CV (opcional)
            limit: Límite de resultados
            
        Returns:
            Lista de sesiones
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if cv_id:
            cursor.execute("""
                SELECT * FROM interview_sessions 
                WHERE cv_id = ? 
                ORDER BY created_at DESC LIMIT ?
            """, (cv_id, limit))
        else:
             cursor.execute("""
                SELECT * FROM interview_sessions 
                ORDER BY created_at DESC LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
