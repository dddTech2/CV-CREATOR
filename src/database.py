"""
Gestor de base de datos SQLite para el historial de CVs generados.
"""
import sqlite3
from pathlib import Path

from src.logger import get_logger

logger = get_logger(__name__)


class CVDatabase:
    def __init__(self, db_path: str = "data/cv_history.db"):
        self.db_path = db_path
        self._init_db()

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
