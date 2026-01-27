"""
Módulo para renderizar archivos YAML a PDF usando RenderCV.

Este módulo proporciona la clase PDFRenderer que integra con la biblioteca
RenderCV para generar PDFs profesionales a partir de archivos YAML de CVs.
"""
import os
import shutil
import pathlib
from pathlib import Path
from typing import Optional

from src.logger import get_logger

logger = get_logger(__name__)

try:
    import rendercv
    # RenderCV 2.6+ imports
    from rendercv.schema.rendercv_model_builder import build_rendercv_dictionary_and_model
    from rendercv.renderer.typst import generate_typst
    from rendercv.renderer.pdf_png import generate_pdf
except ImportError:
    raise ImportError(
        "RenderCV no está instalado correctamente. Ejecuta: pip install 'rendercv[full]'"
    )


class PDFRenderError(Exception):
    """Excepción personalizada para errores de renderizado de PDF."""

    pass


class PDFRenderer:
    """
    Renderiza archivos YAML de CVs a PDF usando RenderCV.

    Esta clase maneja la conversión de archivos YAML (compatibles con RenderCV)
    a documentos PDF profesionales. Soporta múltiples temas y maneja la limpieza
    de archivos temporales automáticamente.

    Attributes:
        output_dir (Path): Directorio donde se guardarán los PDFs generados.
        keep_temp_files (bool): Si True, mantiene archivos temporales para debug.
    """

    SUPPORTED_THEMES = ["classic", "sb2nov", "moderncv", "engineeringresumes"]

    def __init__(
        self, output_dir: str | Path = "outputs", keep_temp_files: bool = False
    ):
        """
        Inicializa el renderizador de PDF.

        Args:
            output_dir: Directorio donde guardar los PDFs generados.
            keep_temp_files: Si True, mantiene archivos temporales después del render.
        """
        self.output_dir = Path(output_dir)
        self.keep_temp_files = keep_temp_files

        # Crear directorio de salida si no existe
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(
        self,
        yaml_content: str | None = None,
        yaml_path: str | Path | None = None,
        output_filename: str | None = None,
    ) -> str:
        """
        Renderiza un archivo YAML a PDF.

        Acepta el contenido YAML como string o la ruta a un archivo YAML.
        Al menos uno de los dos parámetros debe ser proporcionado.

        Args:
            yaml_content: Contenido YAML como string.
            yaml_path: Ruta al archivo YAML.
            output_filename: Nombre del archivo PDF de salida (sin extensión).
                           Si no se proporciona, se genera automáticamente.

        Returns:
            str: Ruta absoluta al archivo PDF generado.

        Raises:
            PDFRenderError: Si hay un error durante el renderizado.
            ValueError: Si no se proporciona yaml_content ni yaml_path,
                       o si el archivo YAML no existe.
        """
        # Validar inputs
        if yaml_content is None and yaml_path is None:
            raise ValueError(
                "Debe proporcionar yaml_content o yaml_path, no ambos pueden ser None"
            )

        # Si se proporciona yaml_path, leer el contenido
        if yaml_path is not None:
            yaml_path_obj = Path(yaml_path)
            if not yaml_path_obj.exists():
                raise ValueError(f"El archivo YAML no existe: {yaml_path}")

            with open(yaml_path_obj, "r", encoding="utf-8") as f:
                yaml_content_str = f.read()
        else:
            if yaml_content is None:
                 raise ValueError("yaml_content es None inesperadamente")
            yaml_content_str = yaml_content

        # Determinar nombre del archivo de salida
        if output_filename is None:
            import time

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_filename = f"cv_{timestamp}"

        # Asegurar que no tenga extensión
        output_filename = output_filename.replace(".pdf", "")

        # Ruta completa del PDF de salida
        output_pdf_path = self.output_dir / f"{output_filename}.pdf"

        try:
            logger.info(f"Renderizando PDF desde string. Salida: {output_pdf_path}")
            
            # --- RenderCV 2.6+ Pipeline ---
            # 1. Build Model
            try:
                # Usamos build_rendercv_dictionary_and_model para validar y construir el modelo
                # Pasamos configuración de salida para optimizar (solo PDF)
                dict_data, rendercv_model = build_rendercv_dictionary_and_model(
                    yaml_content_str,
                    pdf_path=output_pdf_path,
                    dont_generate_png=True,
                    dont_generate_html=True,
                    dont_generate_markdown=True
                )
            except Exception as e:
                # Capturar errores de validación de RenderCV
                logger.error(f"Error de validación RenderCV: {e}")
                raise PDFRenderError(f"Error de validación del YAML: {str(e)}")

            # 2. Generate Typst
            try:
                typst_path = generate_typst(rendercv_model)
                if typst_path is None:
                    raise PDFRenderError("Error interno: No se generó el archivo Typst")
            except Exception as e:
                logger.error(f"Error generando Typst: {e}")
                raise PDFRenderError(f"Error generando código Typst: {str(e)}")

            # 3. Generate PDF
            try:
                final_pdf_path = generate_pdf(rendercv_model, typst_path)
                if final_pdf_path is None:
                    raise PDFRenderError("Error interno: No se generó el PDF")
            except Exception as e:
                logger.error(f"Error compilando PDF: {e}")
                raise PDFRenderError(f"Error compilando PDF (Typst): {str(e)}")

            # --------------------------------

            # Verificar que el PDF tiene contenido
            if output_pdf_path.stat().st_size == 0:
                logger.error("El PDF generado está vacío")
                raise PDFRenderError(f"El PDF generado está vacío: {output_pdf_path}")

            logger.info("PDF generado exitosamente")
            return str(output_pdf_path.absolute())

        except Exception as e:
            if isinstance(e, PDFRenderError):
                raise
            
            logger.error(f"Error al renderizar PDF: {e}", exc_info=True)
            raise PDFRenderError(f"Error al renderizar PDF: {str(e)}") from e

    def render_from_file(
        self, yaml_file_path: str | Path, output_filename: str | None = None
    ) -> str:
        """Renderiza un archivo YAML a PDF (método de conveniencia)."""
        return self.render(yaml_path=yaml_file_path, output_filename=output_filename)

    def render_from_string(
        self, yaml_string: str, output_filename: str | None = None
    ) -> str:
        """Renderiza contenido YAML (como string) a PDF (método de conveniencia)."""
        return self.render(yaml_content=yaml_string, output_filename=output_filename)

    def batch_render(
        self, yaml_files: list[str | Path], output_dir: str | Path | None = None
    ) -> list[str]:
        """Renderiza múltiples archivos YAML a PDF en batch."""
        original_output_dir = self.output_dir

        if output_dir is not None:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)

        pdf_paths = []
        errors = []

        try:
            for yaml_file in yaml_files:
                try:
                    yaml_path = Path(yaml_file)
                    output_name = yaml_path.stem
                    pdf_path = self.render_from_file(yaml_file, output_name)
                    pdf_paths.append(pdf_path)
                except Exception as e:
                    errors.append((yaml_file, str(e)))

            if errors:
                error_msg = "\n".join(
                    [f"  - {file}: {error}" for file, error in errors]
                )
                raise PDFRenderError(
                    f"Errores al renderizar {len(errors)} archivo(s):\n{error_msg}"
                )

            return pdf_paths

        finally:
            self.output_dir = original_output_dir

    def cleanup_output_dir(self, keep_pdfs: bool = True) -> int:
        """Limpia archivos temporales del directorio de salida."""
        if not self.output_dir.exists():
            return 0

        count = 0
        for file_path in self.output_dir.iterdir():
            if file_path.is_file():
                if keep_pdfs and file_path.suffix.lower() == ".pdf":
                    continue

                try:
                    file_path.unlink()
                    count += 1
                except Exception:
                    pass

        return count

    def validate_yaml_for_rendering(self, yaml_content: str) -> tuple[bool, str]:
        """Valida que el contenido YAML sea válido para RenderCV."""
        try:
            # Usar la nueva API de validación
            build_rendercv_dictionary_and_model(yaml_content)
            return True, ""
        except Exception as e:
            return False, str(e)

    def get_output_dir(self) -> Path:
        return self.output_dir

    def __repr__(self) -> str:
        return (
            f"PDFRenderer(output_dir='{self.output_dir}', "
            f"keep_temp_files={self.keep_temp_files})"
        )
