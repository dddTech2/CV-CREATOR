"""
Tests unitarios para el procesador de CVs.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import PyPDF2
from src.cv_parser import (
    CVParser,
    CVData,
    CVParserError,
    PDFParseError
)


class TestCVData:
    """Tests para la dataclass CVData."""
    
    def test_is_empty_with_empty_text(self):
        """Test is_empty con texto vacío."""
        cv_data = CVData(raw_text="", sections={}, metadata={})
        assert cv_data.is_empty
    
    def test_is_empty_with_whitespace(self):
        """Test is_empty con solo espacios."""
        cv_data = CVData(raw_text="   \n\t  ", sections={}, metadata={})
        assert cv_data.is_empty
    
    def test_is_not_empty(self):
        """Test is_empty con contenido."""
        cv_data = CVData(raw_text="John Doe CV", sections={}, metadata={})
        assert not cv_data.is_empty


class TestCVParser:
    """Tests para la clase CVParser."""
    
    def test_init(self):
        """Test inicialización del parser."""
        parser = CVParser()
        assert parser.supported_formats == ['.pdf', '.txt']
    
    def test_parse_text_success(self):
        """Test parseo exitoso de texto plano."""
        parser = CVParser()
        text = """
        John Doe
        Software Engineer
        
        Experience:
        - Company A (2020-2023)
        
        Education:
        - University X
        
        Skills:
        - Python, JavaScript
        """
        
        cv_data = parser.parse_text(text)
        
        assert not cv_data.is_empty
        assert "John Doe" in cv_data.raw_text
        assert cv_data.metadata['format'] == 'text'
        assert cv_data.metadata['length'] > 0
        # Verificar detección de secciones
        assert 'experience' in cv_data.sections
        assert 'education' in cv_data.sections
        assert 'skills' in cv_data.sections
    
    def test_parse_text_empty_raises_error(self):
        """Test que falla con texto vacío."""
        parser = CVParser()
        
        with pytest.raises(CVParserError, match="texto del CV está vacío"):
            parser.parse_text("")
    
    def test_parse_text_whitespace_only_raises_error(self):
        """Test que falla con solo espacios."""
        parser = CVParser()
        
        with pytest.raises(CVParserError, match="texto del CV está vacío"):
            parser.parse_text("   \n\t  ")
    
    def test_parse_text_multilanguage_sections(self):
        """Test detección de secciones en múltiples idiomas."""
        parser = CVParser()
        
        # Español
        text_es = "Experiencia Laboral\nEducación\nHabilidades"
        cv_es = parser.parse_text(text_es)
        assert 'experience' in cv_es.sections
        assert 'education' in cv_es.sections
        assert 'skills' in cv_es.sections
        
        # English
        text_en = "Work Experience\nEducation\nSkills"
        cv_en = parser.parse_text(text_en)
        assert 'experience' in cv_en.sections
        assert 'education' in cv_en.sections
        assert 'skills' in cv_en.sections
    
    def test_parse_pdf_with_file_path(self, tmp_path):
        """Test parseo de PDF desde archivo."""
        # Crear un PDF de prueba simple
        pdf_path = tmp_path / "test_cv.pdf"
        
        # Mock de PyPDF2
        with patch('src.cv_parser.PyPDF2.PdfReader') as mock_reader_class:
            mock_reader = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "John Doe\nSoftware Engineer\nExperience: 5 years"
            mock_reader.pages = [mock_page]
            mock_reader.metadata = {
                '/Title': 'My CV',
                '/Author': 'John Doe'
            }
            mock_reader_class.return_value = mock_reader
            
            # Crear archivo dummy
            pdf_path.write_bytes(b'dummy pdf content')
            
            parser = CVParser()
            cv_data = parser.parse_pdf(file_path=str(pdf_path))
            
            assert not cv_data.is_empty
            assert "John Doe" in cv_data.raw_text
            assert cv_data.metadata['format'] == 'pdf'
            assert cv_data.metadata['num_pages'] == 1
            assert cv_data.metadata['source'] == str(pdf_path)
    
    def test_parse_pdf_with_bytes(self):
        """Test parseo de PDF desde bytes."""
        pdf_bytes = b'dummy pdf content'
        
        with patch('src.cv_parser.PyPDF2.PdfReader') as mock_reader_class:
            mock_reader = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Maria Garcia\nData Scientist"
            mock_reader.pages = [mock_page]
            mock_reader.metadata = None
            mock_reader_class.return_value = mock_reader
            
            parser = CVParser()
            cv_data = parser.parse_pdf(file_bytes=pdf_bytes)
            
            assert "Maria Garcia" in cv_data.raw_text
            assert cv_data.metadata['source'] == 'bytes'
    
    def test_parse_pdf_without_path_or_bytes_raises_error(self):
        """Test que falla sin path ni bytes."""
        parser = CVParser()
        
        with pytest.raises(CVParserError, match="Debe proporcionar file_path o file_bytes"):
            parser.parse_pdf()
    
    def test_parse_pdf_empty_text_raises_error(self):
        """Test que falla cuando PDF no tiene texto extraíble."""
        with patch('src.cv_parser.PyPDF2.PdfReader') as mock_reader_class:
            mock_reader = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = ""
            mock_reader.pages = [mock_page]
            mock_reader_class.return_value = mock_reader
            
            parser = CVParser()
            
            with pytest.raises(PDFParseError, match="No se pudo extraer texto"):
                parser.parse_pdf(file_bytes=b'dummy')
    
    def test_parse_pdf_file_not_found(self):
        """Test error cuando archivo no existe."""
        parser = CVParser()
        
        with pytest.raises(CVParserError, match="Archivo no encontrado"):
            parser.parse_pdf(file_path="/nonexistent/file.pdf")
    
    def test_parse_pdf_corrupted_raises_error(self, tmp_path):
        """Test error con PDF corrupto."""
        pdf_path = tmp_path / "corrupted.pdf"
        pdf_path.write_bytes(b'not a valid pdf')
        
        with patch('src.cv_parser.PyPDF2.PdfReader') as mock_reader_class:
            mock_reader_class.side_effect = PyPDF2.errors.PdfReadError("Invalid PDF")
            
            parser = CVParser()
            
            with pytest.raises(PDFParseError, match="Error al leer el PDF"):
                parser.parse_pdf(file_path=str(pdf_path))
    
    def test_parse_pdf_multipage(self):
        """Test parseo de PDF con múltiples páginas."""
        with patch('src.cv_parser.PyPDF2.PdfReader') as mock_reader_class:
            mock_reader = Mock()
            
            # Crear 3 páginas
            mock_page1 = Mock()
            mock_page1.extract_text.return_value = "Page 1: John Doe"
            
            mock_page2 = Mock()
            mock_page2.extract_text.return_value = "Page 2: Experience"
            
            mock_page3 = Mock()
            mock_page3.extract_text.return_value = "Page 3: Education"
            
            mock_reader.pages = [mock_page1, mock_page2, mock_page3]
            mock_reader.metadata = None
            mock_reader_class.return_value = mock_reader
            
            parser = CVParser()
            cv_data = parser.parse_pdf(file_bytes=b'dummy')
            
            assert cv_data.metadata['num_pages'] == 3
            assert "Page 1" in cv_data.raw_text
            assert "Page 2" in cv_data.raw_text
            assert "Page 3" in cv_data.raw_text
    
    def test_parse_file_pdf(self, tmp_path):
        """Test parse_file con PDF."""
        pdf_path = tmp_path / "cv.pdf"
        pdf_path.write_bytes(b'dummy')
        
        with patch('src.cv_parser.PyPDF2.PdfReader') as mock_reader_class:
            mock_reader = Mock()
            mock_page = Mock()
            mock_page.extract_text.return_value = "Test CV"
            mock_reader.pages = [mock_page]
            mock_reader.metadata = None
            mock_reader_class.return_value = mock_reader
            
            parser = CVParser()
            cv_data = parser.parse_file(str(pdf_path))
            
            assert cv_data.metadata['format'] == 'pdf'
    
    def test_parse_file_txt(self, tmp_path):
        """Test parse_file con TXT."""
        txt_path = tmp_path / "cv.txt"
        txt_path.write_text("John Doe\nSoftware Engineer", encoding='utf-8')
        
        parser = CVParser()
        cv_data = parser.parse_file(str(txt_path))
        
        assert cv_data.metadata['format'] == 'text'
        assert "John Doe" in cv_data.raw_text
    
    def test_parse_file_unsupported_format(self, tmp_path):
        """Test error con formato no soportado."""
        doc_path = tmp_path / "cv.docx"
        doc_path.write_bytes(b'dummy')
        
        parser = CVParser()
        
        with pytest.raises(CVParserError, match="Formato no soportado"):
            parser.parse_file(str(doc_path))
    
    def test_parse_file_not_exists(self):
        """Test error cuando archivo no existe."""
        parser = CVParser()
        
        with pytest.raises(CVParserError, match="Archivo no encontrado"):
            parser.parse_file("/nonexistent/cv.pdf")
    
    def test_get_preview_short_text(self):
        """Test preview con texto corto."""
        parser = CVParser()
        cv_data = CVData(
            raw_text="Short CV",
            sections={},
            metadata={}
        )
        
        preview = parser.get_preview(cv_data, max_chars=100)
        assert preview == "Short CV"
        assert "..." not in preview
    
    def test_get_preview_long_text(self):
        """Test preview con texto largo."""
        parser = CVParser()
        long_text = "A" * 1000
        cv_data = CVData(
            raw_text=long_text,
            sections={},
            metadata={}
        )
        
        preview = parser.get_preview(cv_data, max_chars=100)
        assert len(preview) == 103  # 100 + "..."
        assert preview.endswith("...")
    
    def test_get_statistics(self):
        """Test obtención de estadísticas."""
        parser = CVParser()
        text = """
        John Doe
        Software Engineer
        
        Experience at Company A
        """
        cv_data = CVData(
            raw_text=text,
            sections={'experience': 'detected'},
            metadata={'format': 'text'}
        )
        
        stats = parser.get_statistics(cv_data)
        
        assert stats['total_characters'] == len(text)
        assert stats['total_words'] > 0
        assert stats['total_lines'] > 0
        assert stats['avg_words_per_line'] > 0
        assert stats['sections_detected'] == ['experience']
        assert stats['format'] == 'text'
    
    def test_extract_basic_sections_no_sections(self):
        """Test extracción cuando no hay secciones claras."""
        parser = CVParser()
        text = "Just some random text without clear sections"
        
        sections = parser._extract_basic_sections(text)
        
        # Puede estar vacío o no, depende del texto
        assert isinstance(sections, dict)
    
    def test_extract_basic_sections_with_summary(self):
        """Test detección de sección summary/perfil."""
        parser = CVParser()
        
        texts = [
            "Resumen: Ingeniero de software",
            "Summary: Software Engineer",
            "Sobre mí: Desarrollador Python"
        ]
        
        for text in texts:
            sections = parser._extract_basic_sections(text)
            assert 'summary' in sections
