"""
Tests para el sistema de logging.
"""
import os
import logging
import pytest
from pathlib import Path
from src.logger import setup_logger, get_logger, LOG_FILE

def test_logger_setup():
    """Test que el logger se configura correctamente."""
    logger = setup_logger("test_logger")
    
    assert logger.level == logging.INFO
    assert len(logger.handlers) >= 2  # Console + File
    
    # Verificar que el archivo de log existe (o se crea al escribir)
    logger.info("Test log message")
    assert LOG_FILE.exists()

def test_get_logger_returns_same_instance():
    """Test que get_logger retorna la misma instancia para el mismo nombre."""
    logger1 = get_logger("same_name")
    logger2 = get_logger("same_name")
    
    assert logger1 is logger2

def test_logger_rotation():
    """Test básico de que el handler es rotativo (no prueba rotación real por tamaño)."""
    logger = get_logger("rotation_test")
    file_handler = [h for h in logger.handlers if hasattr(h, 'baseFilename')][0]
    
    assert file_handler.baseFilename == str(LOG_FILE.absolute())
    assert file_handler.maxBytes > 0
    assert file_handler.backupCount > 0
