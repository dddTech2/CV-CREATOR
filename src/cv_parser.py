"""
Procesador de CVs: extracción de texto de diferentes formatos.

Soporta texto plano y PDFs.
"""
import io
from pathlib import Path
from typing import Dict, Optional, Union
from dataclasses import dataclass
import PyPDF2

from src.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CVData:
    """Estructura de datos para un CV parseado."""
    raw_text: str
    sections: Dict[str, str]
    metadata: Dict[str, any]
    
    @property
    def is_empty(self) -> bool:
        """Retorna True si el CV no tiene contenido."""
        return len(self.raw_text.strip()) == 0


class CVParserError(Exception):
    """Excepción base para errores del parser."""
    pass


class PDFParseError(CVParserError):
    """Excepción para errores al parsear PDFs."""
    pass


class CVParser:
    """
    Parser de CVs que extrae texto de diferentes formatos.
    
    Soporta:
    - Texto plano
    - PDF (con texto seleccionable, no OCR)
    """
    
    def __init__(self):
        """Inicializa el parser de CVs."""
        self.supported_formats = ['.pdf', '.txt']
    
    def parse_text(self, text: str) -> CVData:
        """
        Parsea un CV en formato texto plano.
        
        Args:
            text: Contenido del CV en texto plano
            
        Returns:
            CVData con el texto parseado
            
        Raises:
            CVParserError: Si el texto está vacío
        """
        if not text or not text.strip():
            raise CVParserError("El texto del CV está vacío")
        
        # Por ahora, simplemente guardamos el texto raw
        # En futuras versiones podríamos usar NLP para extraer secciones
        return CVData(
            raw_text=text.strip(),
            sections=self._extract_basic_sections(text),
            metadata={
                'format': 'text',
                'length': len(text),
                'lines': len(text.splitlines())
            }
        )
    
    def parse_pdf(
        self,
        file_path: Optional[str] = None,
        file_bytes: Optional[bytes] = None
    ) -> CVData:
        """
        Parsea un CV en formato PDF.
        ...
        """
        if not file_path and not file_bytes:
            raise CVParserError("Debe proporcionar file_path o file_bytes")
        
        try:
            logger.info(f"Iniciando parsing de PDF: {'archivo' if file_path else 'bytes'}")
            
            # Abrir el PDF
            if file_path:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text, metadata = self._extract_from_pdf_reader(pdf_reader)
                    metadata['source'] = file_path
            else:
                pdf_file = io.BytesIO(file_bytes)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text, metadata = self._extract_from_pdf_reader(pdf_reader)
                metadata['source'] = 'bytes'
            
            if not text.strip():
                logger.warning("PDF parseado pero sin texto extraíble")
                raise PDFParseError(
                    "No se pudo extraer texto del PDF. "
                    "Asegúrate de que el PDF tenga texto seleccionable (no sea una imagen escaneada)."
                )
            
            logger.info(f"PDF parseado exitosamente. Longitud: {len(text)} caracteres")
            return CVData(
                raw_text=text.strip(),
                sections=self._extract_basic_sections(text),
                metadata=metadata
            )
            
        except PyPDF2.errors.PdfReadError as e:
            logger.error(f"Error de lectura PDF: {e}")
            raise PDFParseError(f"Error al leer el PDF: {str(e)}")
        except FileNotFoundError:
            logger.error(f"Archivo no encontrado: {file_path}")
            raise CVParserError(f"Archivo no encontrado: {file_path}")
        except Exception as e:
            if isinstance(e, (PDFParseError, CVParserError)):
                raise
            logger.error(f"Error inesperado parsing PDF: {e}", exc_info=True)
            raise PDFParseError(f"Error inesperado al parsear PDF: {str(e)}")
    
    def _extract_from_pdf_reader(self, pdf_reader: PyPDF2.PdfReader) -> tuple[str, Dict]:
        """
        Extrae texto y metadata de un PdfReader.
        
        Args:
            pdf_reader: Instancia de PyPDF2.PdfReader
            
        Returns:
            Tupla (texto_extraído, metadata)
        """
        # Extraer texto de todas las páginas
        text_parts = []
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            except Exception as e:
                # Log warning pero continuar con otras páginas
                print(f"Warning: Error extrayendo página {page_num + 1}: {e}")
        
        full_text = "\n\n".join(text_parts)
        
        # Extraer metadata del PDF
        metadata = {
            'format': 'pdf',
            'num_pages': len(pdf_reader.pages),
            'length': len(full_text),
            'lines': len(full_text.splitlines())
        }
        
        # Intentar extraer metadata adicional
        if pdf_reader.metadata:
            metadata['pdf_metadata'] = {
                'title': pdf_reader.metadata.get('/Title', ''),
                'author': pdf_reader.metadata.get('/Author', ''),
                'creator': pdf_reader.metadata.get('/Creator', ''),
            }
        
        return full_text, metadata
    
    def _extract_basic_sections(self, text: str) -> Dict[str, str]:
        """
        Intenta extraer secciones básicas del CV.
        
        Esta es una implementación simple que busca palabras clave comunes.
        En futuras versiones se podría usar NLP más sofisticado.
        
        Args:
            text: Texto completo del CV
            
        Returns:
            Diccionario con secciones identificadas
        """
        sections = {}
        text_lower = text.lower()
        
        # Palabras clave para identificar secciones (multilenguaje)
        section_keywords = {
            'experience': [
                'experiencia', 'experience', 'experiência', 'expérience',
                'trabajo', 'work', 'trabalho', 'travail',
                'empleo', 'employment', 'emploi'
            ],
            'education': [
                'educación', 'education', 'educação', 'éducation',
                'formación', 'training', 'formação', 'formation',
                'estudios', 'studies', 'estudos', 'études'
            ],
            'skills': [
                'habilidades', 'skills', 'competências', 'compétences',
                'tecnologías', 'technologies', 'tecnologias',
                'herramientas', 'tools', 'ferramentas', 'outils'
            ],
            'summary': [
                'resumen', 'summary', 'resumo', 'résumé',
                'perfil', 'profile', 'sobre mí', 'about',
                'objetivo', 'objective', 'objectif'
            ]
        }
        
        # Buscar secciones
        for section_name, keywords in section_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    sections[section_name] = 'detected'
                    break
        
        return sections
    
    def parse_file(self, file_path: str) -> CVData:
        """
        Parsea un archivo de CV detectando automáticamente el formato.
        
        Args:
            file_path: Ruta al archivo
            
        Returns:
            CVData parseado
            
        Raises:
            CVParserError: Si el formato no es soportado o hay error al parsear
        """
        path = Path(file_path)
        
        if not path.exists():
            raise CVParserError(f"Archivo no encontrado: {file_path}")
        
        suffix = path.suffix.lower()
        
        if suffix == '.pdf':
            return self.parse_pdf(file_path=file_path)
        elif suffix == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return self.parse_text(text)
        else:
            raise CVParserError(
                f"Formato no soportado: {suffix}. "
                f"Formatos soportados: {', '.join(self.supported_formats)}"
            )
    
    def get_preview(self, cv_data: CVData, max_chars: int = 500) -> str:
        """
        Obtiene un preview del CV parseado.
        
        Args:
            cv_data: Datos del CV
            max_chars: Máximo de caracteres para el preview
            
        Returns:
            String con el preview
        """
        preview = cv_data.raw_text[:max_chars]
        if len(cv_data.raw_text) > max_chars:
            preview += "..."
        return preview
    
    def get_statistics(self, cv_data: CVData) -> Dict[str, any]:
        """
        Obtiene estadísticas del CV parseado.
        
        Args:
            cv_data: Datos del CV
            
        Returns:
            Diccionario con estadísticas
        """
        text = cv_data.raw_text
        words = text.split()
        
        return {
            'total_characters': len(text),
            'total_words': len(words),
            'total_lines': len(text.splitlines()),
            'avg_words_per_line': len(words) / max(len(text.splitlines()), 1),
            'sections_detected': list(cv_data.sections.keys()),
            'format': cv_data.metadata.get('format', 'unknown')
        }
